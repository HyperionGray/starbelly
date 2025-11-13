import 'package:convert/convert.dart' as convert;

import 'package:starbelly/protobuf/starbelly.pb.dart' as pb;

/// A CAPTCHA solving service.
///
/// Currently implements only the Antigate-style CAPTCHA solver.
class CaptchaSolver {
    String name;
    String solverId;
    DateTime createdAt, updatedAt;
    String serviceUrl = '';
    String apiKey = '';
    bool requirePhrase;
    bool caseSensitive;
    pb.CaptchaSolverAntigateCharacters characters;
    bool requireMath;
    String minLength = '', maxLength = '';

    /// Default constructor.
    CaptchaSolver(this.name) {
        this.requirePhrase = false;
        this.caseSensitive = false;
        this.characters = pb.CaptchaSolverAntigateCharacters.ALPHANUMERIC;
        this.requireMath = false;
    }

    /// Instantiate a CAPTCHA solver from another CAPTCHA solver object.
    CaptchaSolver.copy(CaptchaSolver solver) {
        this.name = solver.name + ' (Copy)';
        this.serviceUrl = solver.serviceUrl;
        this.apiKey = solver.apiKey;
        this.requirePhrase = solver.requirePhrase;
        this.caseSensitive = solver.caseSensitive;
        this.characters = solver.characters;
        this.requireMath = solver.requireMath;
        this.minLength = solver.minLength;
        this.maxLength = solver.maxLength;
    }

    /// Instantiate a CAPTCHA solver from a protobuf message.
    CaptchaSolver.fromPb(pb.CaptchaSolver pbSolver) {
        this.solverId = convert.hex.encode(pbSolver.solverId);
        this.name = pbSolver.name;
        this.createdAt = DateTime.parse(pbSolver.createdAt).toLocal();
        this.updatedAt = DateTime.parse(pbSolver.updatedAt).toLocal();
        this.serviceUrl = pbSolver.antigate.serviceUrl;
        this.apiKey = pbSolver.antigate.apiKey;
        this.requirePhrase = pbSolver.antigate.requirePhrase;
        this.caseSensitive = pbSolver.antigate.caseSensitive;
        this.characters = pbSolver.antigate.characters;
        this.requireMath = pbSolver.antigate.requireMath;
        if (pbSolver.antigate.hasMinLength()) {
            this.minLength = pbSolver.antigate.minLength.toString();
        }
        if (pbSolver.antigate.hasMaxLength()) {
            this.maxLength = pbSolver.antigate.maxLength.toString();
        }
    }

    /// Convert to protobuf object.
    pb.CaptchaSolver toPb() {
        var pbSolver = new pb.CaptchaSolver()
            ..name = this.name;
        if (this.solverId != null) {
            pbSolver.solverId = convert.hex.decode(this.solverId);
        }
        pbSolver.antigate = new pb.CaptchaSolverAntigate()
            ..serviceUrl = this.serviceUrl
            ..apiKey = this.apiKey
            ..requirePhrase = this.requirePhrase
            ..caseSensitive = this.caseSensitive
            ..characters = this.characters
            ..requireMath = this.requireMath;
        if (this.minLength.isNotEmpty) {
            pbSolver.antigate.minLength = int.parse(this.minLength, radix: 10);
        }
        if (this.maxLength.isNotEmpty) {
            pbSolver.antigate.maxLength = int.parse(this.maxLength, radix: 10);
        }
        return pbSolver;
    }
}
