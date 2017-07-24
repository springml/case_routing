app.controller("DashboardController", function($scope, $location, $http, anchorSmoothScroll, DataService) {
    // Initialize Chart variables
    $scope.labesCategory;
    $scope.dataCategory;
    $scope.optionsCategory;
    $scope.colorsCategory;

    $scope.labelsAssignee;
    $scope.dataAssignee;
    $scope.optionsAssignee;
    $scope.colorsAssignee;

    $scope.rawData

    $scope.chart;
    $scope.line = "line";
    $scope.bar = "bar";
    $scope.radar = "radar";
    $scope.doughnut = "doughnut";
    $scope.pie = "pie";
    $scope.horizontalBar = "horizontalBar";

    $scope.title = "Analytics Controller";

    DataService.getAllData().then(function(data){
        $scope.rawData = data.reverse();
    });

    // Cases VS. Time
    DataService.getCasesVSTime().then(function(res){
        $scope.labelsDate = res[0];
        $scope.dataDate = res[1];
        $scope.optionsDate = barOptions("Cases vs Time");
        $scope.colorsAssignee = [
            "#E0F2F1", "#B2DFDB", "#80CBC4",
            "#4DB6AC", "#26A69A", "#009688",
            "#00897B", "#00796B", "#00695C"
        ];
    });
    // Cases Per Region
    DataService.getCasesVSRegion().then(function(res){
        $scope.labelsRegion = res[0];
        $scope.dataRegion = res[1];
        $scope.optionsRegion = barOptions("Cases per Region");
        $scope.colorsRegion = [
            "#C8E6C9", "#A5D6A7", "#81C784",
            "#66BB6A", "#4CAF50", "#43A047",
            "#388E3C", "#2E7D32", "#1B5E20"
        ];
    });
    // Cases Per Category
    DataService.getCasesVSCategory().then(function(res){
        $scope.labelsCategory = res[0];
        $scope.dataCategory = res[1];
        $scope.optionsCategory = barOptions("Cases per Category");
        $scope.colorsCategory = [
            "#E1F5FE", "#B3E5FC", "#81D4FA",
            "#4FC3F7", "#29B6F6", "#03A9F4",
            "#039BE5", "#0288D1", "#0277BD"
        ];
    });
    // Cases Per Assignee
    DataService.getCasesVSAssignee().then(function(res){
        $scope.labelsAssignee = res[0];
        $scope.dataAssignee = res[1];
        $scope.optionsAssignee = horizontalBarOptions("Cases per Assignee");
        $scope.colorsAssignee = [
            "#E0F2F1", "#B2DFDB", "#80CBC4",
            "#4DB6AC", "#26A69A", "#009688",
            "#00897B", "#00796B", "#00695C"
        ];
    });

    $scope.datasetOverride = [{
        backgroundColour: ['#000000']
    }]
    $scope.showData = function(event) {
        console.log(event);
    }
    $scope.gotoElement = function(eID) {
        // set the location.hash to the id of
        // the element you wish to scroll to.
        $location.hash('bottom');
        // call $anchorScroll()
        anchorSmoothScroll.scrollTo(eID);
    };
});

app.controller("EmailUsController", function($scope, $location, $http, anchorSmoothScroll) {
    $scope.submitEmail = function(subject, content, priority) {
        if (subject && content && priority) {
            $http.post("/submit", {
                subject: subject,
                content: content,
                priority: priority
            }).then(function(response){
                $scope.subject = "";
                $scope.content = "";
                $scope.priority = "";
            });
        }
    }
});

app.controller("TicketsController", function($scope, $location, $http, DataService, anchorSmoothScroll) {
    $scope.rawData;
    $scope.allCategories;

    DataService.getAllData().then(function(data){
        $scope.rawData = data.reverse();
        $scope.allCategories = findAllCategories(data);
    });

    $scope.notHidden = false;
    $scope.leftPaneCaseID;
    $scope.rightPaneCaseID;
    $scope.changeBool = function(row, id) {
        $scope.rightPaneCaseID = id;
        // Right panel opens or close, depending on which button is clicked
        if ($scope.notHidden === false) {
            $scope.notHidden = true
        } else {
            $scope.notHidden = false;
        }
    }
    $scope.modifyCategory = function(modCat, id){
        // console.log(id);
        // console.log(modCat);
        if(modCat && id){
            $http.post("/modifyCategory", {
                Category: modCat,
                CaseID: id
            }).then(function(response){
                console.log("I'm here!");
            });
        }
        $scope.notHidden = false;
    }
});

// User Defined Functions
function circleOptions(titleText) {
    return {
        options: {
            responsive: true,
            maintainAspectRatio: false
        },
        title: {
            display: true,
            text: titleText,
            fontSize: 20
        }
    }
}

function barOptions(titleText) {
    return {
        options: {
            responsive: true,
            maintainAspectRatio: false
        },
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
            yAxes: [
                {
                    id: "y-axis-1",
                    type: "linear",
                    display: true,
                    position: "left",
                    ticks: {
                        beginAtZero: true,
                        callback: function (value) { if (Number.isInteger(value)) { return value; } },
                        stepSize: 1
                    }
                }
            ]
        }
    }
}

function horizontalBarOptions(titleText) {
    return {
        options: {
            responsive: true,
            maintainAspectRatio: false
        },
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
            xAxes: [
                {
                    id: "x-axis-1",
                    display: true,
                    position: "left",
                    ticks: {
                        beginAtZero: true,
                        callback: function (value) { if (Number.isInteger(value)) { return value; } },
                        stepSize: 1
                    }
                }
            ]
        }
    }
}

function findAllCategories(arr){
    var retArr = [];
    arr.forEach(function(dataRow){
        if(retArr.indexOf(dataRow.Category) === -1){
            retArr.push(dataRow.Category);
        }
    });
    return retArr;
}
