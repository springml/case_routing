var app = angular.module("app", ['ngRoute', 'chart.js']);
app.config(function($routeProvider, $locationProvider){
    $routeProvider.when('/', {
        templateUrl: "./views/analytics.html",
        controller: "AnalyticsController"
    }).when('/tickets', {
        templateUrl: "./views/tickets.html",
        controller: "TicketsController"
    }).when('/email-us', {
        templateUrl: "./views/email-us.html",
        controller: "EmailUsController"
    }).otherwise({
        redirectTo: "/"
    });

    $locationProvider.html5Mode({
        enabled: true,
        requireBase: false
    });
});
