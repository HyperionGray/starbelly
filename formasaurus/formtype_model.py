"""
This module defines which features and which classifier the default
form type detection model uses.
"""

import numpy as np
from sklearn.feature_extraction import DictVectorizer
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import GroupKFold, cross_val_predict
from sklearn.pipeline import make_pipeline, make_union
from sklearn.svm import LinearSVC

from formasaurus import formtype_features as features
from formasaurus.utils import get_domain

# a list of 3-tuples with default features:
# (feature_name, form_transformer, vectorizer)
FEATURES = [
    ("form elements", features.FormElements(), DictVectorizer()),
    (
        "<input type=submit value=...>",
        features.SubmitText(),
        CountVectorizer(ngram_range=(1, 2), min_df=1, binary=True),
    ),
    # (
    #     "<form> TEXT </form>",
    #     features.FormText(),
    #     TfidfVectorizer(ngram_range=(1,2), min_df=5, stop_words='english',
    #                     binary=True)
    # ),
    (
        "<a> TEXT </a>",
        features.FormLinksText(),
        TfidfVectorizer(
            ngram_range=(1, 2), min_df=4, binary=True, stop_words=["and", "or", "of"]
        ),
    ),
    (
        "<label> TEXT </label>",
        features.FormLabelText(),
        TfidfVectorizer(
            ngram_range=(1, 2), min_df=3, binary=True, stop_words="english"
        ),
    ),
    (
        "<form action=...>",
        features.FormUrl(),
        TfidfVectorizer(ngram_range=(5, 6), min_df=4, binary=True, analyzer="char_wb"),
    ),
    (
        "<form class=... id=...>",
        features.FormCss(),
        TfidfVectorizer(ngram_range=(4, 5), min_df=3, binary=True, analyzer="char_wb"),
    ),
    (
        "<input class=... id=...>",
        features.FormInputCss(),
        TfidfVectorizer(ngram_range=(4, 5), min_df=5, binary=True, analyzer="char_wb"),
    ),
    (
        "<input name=...>",
        features.FormInputNames(),
        TfidfVectorizer(ngram_range=(5, 6), min_df=3, binary=True, analyzer="char_wb"),
    ),
    (
        "<input title=...>",
        features.FormInputTitle(),
        TfidfVectorizer(ngram_range=(5, 6), min_df=3, binary=True, analyzer="char_wb"),
    ),
]


def _create_feature_union(features):
    """
    Create a FeatureUnion.
    Each "feature" is a 3-tuple: (name, feature_extractor, vectorizer).
    """
    return make_union(*[make_pipeline(fe, vec) for name, fe, vec in features])


_PROB_CLF_CLASS = LogisticRegression


def _is_prob_clf(clf):
    return isinstance(clf, _PROB_CLF_CLASS)


def _get_prob_clf():
    return _PROB_CLF_CLASS(penalty="l2", C=5, fit_intercept=True)


def _get_non_prob_clf():
    return LinearSVC(C=0.5, random_state=0, fit_intercept=True)


def get_model(prob=True):
    """
    Return a default model.
    """
    # XXX: fit_intercept is False for easier model debugging.
    # Intercept is included as a regular feature ("Bias").

    clf = _get_prob_clf() if prob else _get_non_prob_clf()
    fe = _create_feature_union(FEATURES)
    return make_pipeline(fe, clf)


_VECTORIZER_INIT_ATTRIBUTES = {
    "CountVectorizer": ("ngram_range", "min_df", "binary"),
    "DictVectorizer": tuple(),
    "TfidfVectorizer": ("ngram_range", "min_df", "binary", "stop_words", "analyzer"),
}
_VECTORIZER_NON_INIT_ATTRIBUTES = {
    "CountVectorizer": ("vocabulary_",),
    "DictVectorizer": ("feature_names_", "vocabulary_"),
    "TfidfVectorizer": ("idf_", "vocabulary_"),
}


def to_dict(pipeline):
    clf = pipeline.steps[1][1]
    if not _is_prob_clf(clf):
        raise NotImplementedError(
            f"{clf.__class__.__name__} serialization is not implemented"
        )

    def serialize_value(value):
        metadata = {}
        if isinstance(value, np.ndarray):
            value = value.tolist()
            metadata["type"] = "np.array"
        return {
            "value": value,
            **metadata,
        }

    def vectorizer_to_dict(vectorizer):
        vectorizer_cls = vectorizer.__class__.__name__
        if vectorizer_cls not in _VECTORIZER_INIT_ATTRIBUTES:
            raise NotImplementedError(
                f"Serialization of vectorizers of class {vectorizer_cls} is "
                f"not implemented."
            )
        return {
            "cls": vectorizer_cls,
            "init": {
                attribute: serialize_value(getattr(vectorizer, attribute))
                for attribute in _VECTORIZER_INIT_ATTRIBUTES[vectorizer_cls]
            },
            **{
                attribute: serialize_value(getattr(vectorizer, attribute))
                for attribute in _VECTORIZER_NON_INIT_ATTRIBUTES[vectorizer_cls]
            },
        }

    return {
        "classes": clf.classes_.tolist(),
        "coef": clf.coef_.tolist(),
        "features": [
            (
                transformer.__class__.__name__,
                vectorizer_to_dict(vectorizer),
            )
            for _, transformer, vectorizer in FEATURES
        ],
        "intercept": clf.intercept_.tolist(),
    }


VECTORIZER_CLASSES = {
    "CountVectorizer": CountVectorizer,
    "DictVectorizer": DictVectorizer,
    "TfidfVectorizer": TfidfVectorizer,
}


def from_dict(obj):
    clf = _get_prob_clf()
    clf.classes_ = np.array(obj["classes"])
    clf.coef_ = np.array(obj["coef"])
    clf.intercept_ = np.array(obj["intercept"])

    def unserialize_value(value):
        type_id = value.get("type", None)
        if not type_id:
            return value["value"]
        if type_id == "np.array":
            return np.array(value["value"])
        raise NotImplementedError(
            f"Cannot unserialize value of unexpected type {type_id}"
        )

    def vectorizer_from_dict(data):
        cls_name = data.pop("cls")
        if cls_name not in VECTORIZER_CLASSES:
            raise NotImplementedError(
                f"Cannot unserialize a vectorizer of class {cls_name}"
            )
        vectorizer = VECTORIZER_CLASSES[cls_name](
            **{k: unserialize_value(v) for k, v in data.pop("init").items()}
        )
        for attribute, value in data.items():
            setattr(vectorizer, attribute, unserialize_value(value))
        return vectorizer

    features_ = [
        (
            "_",
            getattr(features, transformer)(),
            vectorizer_from_dict(vectorizer),
        )
        for transformer, vectorizer in obj["features"]
    ]
    fe = _create_feature_union(features_)
    return make_pipeline(fe, clf)


def train(annotations, model=None, full_type_names=False):
    """Train form type detection model on annotation data"""
    if model is None:
        model = get_model()
    X, y = get_Xy(annotations, full_type_names)
    return model.fit(X, y)


def get_Xy(annotations, full_type_names):
    X = [a.form for a in annotations]

    if full_type_names:
        y = np.asarray([a.type_full for a in annotations])
    else:
        y = np.asarray([a.type for a in annotations])

    return X, y


def get_realistic_form_labels(
    annotations, n_splits=10, model=None, full_type_names=True
):
    """
    Return form type labels which form type detection model
    is likely to produce.
    """
    if model is None:
        model = get_model()

    X, y = get_Xy(annotations, full_type_names)
    group_kfold = GroupKFold(n_splits=n_splits)
    groups = [get_domain(ann.url) for ann in annotations]
    return cross_val_predict(model, X, y, cv=group_kfold, groups=groups)


def print_classification_report(annotations, n_splits=10, model=None):
    """Evaluate model, print classification report"""
    if model is None:
        # FIXME: we're overfitting on hyperparameters - they should be chosen
        # using inner cross-validation, not set to fixed values beforehand.
        model = get_model()

    X, y = get_Xy(annotations, full_type_names=True)
    group_kfold = GroupKFold(n_splits=n_splits)
    groups = [get_domain(ann.url) for ann in annotations]
    y_pred = cross_val_predict(model, X, y, cv=group_kfold, groups=groups)

    # hack to format report nicely
    all_labels = list(annotations[0].form_schema.types.keys())
    labels = sorted(set(y_pred), key=lambda k: all_labels.index(k))
    print(
        classification_report(y, y_pred, digits=2, labels=labels, target_names=labels)
    )

    print(
        "{:0.1f}% forms are classified correctly.".format(
            accuracy_score(y, y_pred) * 100
        )
    )
