var app = angular.module("app", ['ngRoute', 'chart.js', 'ngAnimate']);
app.config(function($routeProvider, $locationProvider){
    $routeProvider.when('/', {
        templateUrl: "./views/dashboard.html",
        controller: "DashboardController"
    }).when('/tickets', {
        templateUrl: "./views/tickets.html",
        controller: "TicketsController"
    }).when('/email-us', {
        templateUrl: "./views/email-us.html",
        controller: "EmailUsController"
    }).when('/architecture', {
        templateUrl: "./views/architecture.html",
        controller: "ArchitectureController"
    }).otherwise({
        redirectTo: "/"
    });

    $locationProvider.html5Mode({
        enabled: true,
        requireBase: false
    });
});
