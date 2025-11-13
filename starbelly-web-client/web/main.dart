import 'package:angular/angular.dart';
import 'package:angular_router/angular_router.dart';
import 'package:starbelly/component/app.template.dart' as ng;
import 'main.template.dart' as self;

@GenerateInjector(routerProviders)
final InjectorFactory injector = self.injector$Injector;

void main() {
  runApp(ng.AppComponentNgFactory, createInjector: injector);
}
