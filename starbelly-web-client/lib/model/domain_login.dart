import 'package:starbelly/protobuf/starbelly.pb.dart' as pb;

/// Metadata for authentication.
class DomainLogin {
    String domain;
    String loginUrl;
    String loginTest;
    List<DomainLoginUser> users;

    /// Instantiate a domain login from a protobuf message.
    DomainLogin.fromPb(pb.DomainLogin pbLogin) {
        // These fields should always be present.
        this.domain = pbLogin.domain;
        this.loginUrl = pbLogin.loginUrl;
        this.loginTest = pbLogin.loginTest;
        this.users = new List<DomainLoginUser>.generate(
            pbLogin.users.length,
            (i) => new DomainLoginUser.fromPb(pbLogin.users[i])
        );
    }

    /// Convert to protobuf object.
    pb.DomainLogin toPb() {
        var pbLogin = new pb.DomainLogin()
            ..domain = this.domain
            ..loginUrl = this.loginUrl
            ..loginTest = this.loginTest;
        for (var user in this.users) {
            pbLogin.users.add(user.toPb());
        }
        return pbLogin;
    }
}

/// Contains username and password.
class DomainLoginUser {
    String username;
    String password;
    bool working;

    /// Constructor.
    DomainLoginUser(this.username, this.password) {
        this.working = true;
    }

    /// Instantiate a domain login user from a protobuf message.
    DomainLoginUser.fromPb(pb.DomainLoginUser pbUser) {
        this.username = pbUser.username;
        this.password = pbUser.password;
        this.working = pbUser.working;
    }

    /// Convert to protobuf object.
    pb.DomainLoginUser toPb() {
        var pbUser = new pb.DomainLoginUser()
            ..username = this.username
            ..password = this.password
            ..working = this.working;
        return pbUser;
    }
}
