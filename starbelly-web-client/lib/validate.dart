import 'package:angular_forms/angular_forms.dart';

/// Validate a field contains an integer, with optional min and max.
ValidatorFn integer({int min, int max}) {
    String error;

    if (min == null && max == null) {
        error = 'Must be an integer.';
    } else if (min == null) {
        error = 'Must be an integer less than or equal to $max.';
    } else if (max == null) {
        error = 'Must be an integer greater than or equal to $min.';
    } else {
        error = 'Must be an integer between $min and $max inclusive.';
    }

    return (AbstractControl c) {
        Map<String,dynamic> errors = {};
        String s = c.value.trim();

        try {
            if (s.isNotEmpty) {
                int i = int.parse(s, radix: 10);

                if ((min != null && i < min) || (max != null && i > max)) {
                    errors[error] = '';
                }
            }
        } catch (e) {
            errors[error] = '';
        }

        return errors;
    };
}

/// Validate a field contains a number (integer or floating point), with
/// optional min and max.
ValidatorFn number({num min, num max}) {
    String error;

    if (min == null && max == null) {
        error = 'Must be a number.';
    } else if (min == null) {
        error = 'Must be a number less than or equal to $max.';
    } else if (max == null) {
        error = 'Must be a number greater than or equal to $min.';
    } else {
        error = 'Must be a number between $min and $max inclusive.';
    }

    return (AbstractControl c) {
        Map<String,dynamic> errors = {};
        String s = c.value.trim();

        try {
            if (s.isNotEmpty) {
                num n = double.parse(s);

                if ((min != null && n < min) || (max != null && n > max)) {
                    errors[error] = '';
                }
            }
        } catch (e) {
            errors[error] = '';
        }

        return errors;
    };
}

/// Validate that a field is not empty.
ValidatorFn required() {
    return (AbstractControl c) {
        String s = c.value.trim();
        Map<String,dynamic> errors = {};

        if (s.isEmpty) {
            errors['This field is required.'] = '';
        }

        return errors;
    };
}

/// Validate that a field contains a valid URL.
ValidatorFn url() {
    const String error = 'This field must contain a valid HTTP[S] URL.';

    return (AbstractControl c) {
        String url = c.value.trim();
        Map<String,dynamic> errors = {};

        try {
            var uri = Uri.parse(url);
            if (uri.host.isEmpty || (!uri.scheme.startsWith('http'))) {
                errors[error] = '';
            }
        } catch (e) {
            errors[error] = '';
        }

        return errors;
    };
}
