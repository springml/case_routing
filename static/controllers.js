app.controller("AnalyticsController", function($scope, $location, $http, dataService, rawDataService, anchorSmoothScroll) {
    $scope.chart;
    $scope.line = "line";
    $scope.bar = "bar";
    $scope.radar = "radar";
    $scope.doughnut = "doughnut";
    $scope.pie = "pie";

    $scope.title = "Analytics Controller";
    $scope.rawData = rawDataService;

    // First Chart, Bar Cgart
    $scope.labelsCategory = asArr(rawTransObj(rawDataService, "categoryByUser"), "key");
    $scope.dataCategory = asArr(rawTransObj(rawDataService, "categoryByUser"), "value");
    $scope.optionsCategory = dataOptions("Cases per Cateogry");
    $scope.colorCategory = [
        "#ECEFF1", "#CFD8DC", "#B0BEC5", "#90A4AE",
        "#78909C", "#607D8B", "#546E7A", "#455A64",
        "#37474F", "#263238"
    ]

    // Second Chart, Bar Chart
    $scope.labelsServicer = asArr(rawTransObj(rawDataService, "servicer"), "key");
    $scope.dataServicer = asArr(rawTransObj(rawDataService, "servicer"), "value");
    $scope.optionsServicer = dataOptions("Cases per Asignee");

    // Third Chart, Time Series
    $scope.labelsDate = asArr(rawTransObj(rawDataService, "dateEmailSent"), "key");
    $scope.dataDate = asArr(rawTransObj(rawDataService, "dateEmailSent"), "value");
    $scope.optionsDate = dataOptions("# Cases vs Time");

    // Fourth Chart, Doughnut
    $scope.labelsDate = asArr(rawTransObj(rawDataService, "dateEmailSent"), "key");
    $scope.dataDate = asArr(rawTransObj(rawDataService, "dateEmailSent"), "value");
    $scope.emailsRegion = circleOptions("Cases in Each Region");

    $scope.datasetOverride = [{
        yAxisID: "y-axis-1"
    }, {
        yAxisID: "y-axis-2"
    }];

    $scope.showData = function(event){
        console.log(event);
    }
    $scope.gotoElement = function(eID){
        // set the location.hash to the id of
        // the element you wish to scroll to.
        $location.hash('bottom');
        // call $anchorScroll()
        anchorSmoothScroll.scrollTo(eID);
    };

    $scope.submitEmail = function(subject, content){
        if(subject && content){
            $http.post("/submit", {subject: subject, content: content});
        }

    }
});

function rawTransObj(arr, key){
    var transObj = {};
    arr.forEach(function(row){
        if(!transObj[row[key]]){
            transObj[row[key]] = 1;
        } else {
            transObj[row[key]] += 1;
        }
    })
    return transObj;
}

function asArr(obj, keyOrVal){
    var retArr = [];
    for(var key in obj){
        if(keyOrVal === "key"){
            retArr.push(key);
        } else if (keyOrVal === "value"){
            retArr.push(obj[key]);
        }
    }
    return retArr;
}

function circleOptions(titleText){
    return {
        responsive: true,
        maintainAspectRatio: true,
        title: {
            display: true,
            text: titleText,
            fontSize: 20
        }
    }
}

function dataOptions(titleText){
    return {
        legend: {
            display: false
        },
        elements: {
            line: {
                tension: 0.3,
            }
        },
        title: {
            display: true,
            text: titleText,
            fontSize: 20
        },
        scales: {
            yAxes: [{
                    id: "y-axis-1",
                    type: "linear",
                    display: true,
                    position: "left"
                },
                {
                    id: "y-axis-2",
                    type: "linear",
                    display: false,
                    position: "right"
                }
            ]
        }
    }
}
