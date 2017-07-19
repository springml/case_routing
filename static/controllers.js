app.controller("DashboardController", function($scope, $location, $http, rawDataService, anchorSmoothScroll, DataService) {
    // Initialize Chart variables
    $scope.labesCategory;
    $scope.dataCategory;
    $scope.optionsCategory;
    $scope.colorsCategory;

    $scope.labelsAssignee;
    $scope.dataAssignee;
    $scope.optionsAssignee;
    $scope.colorsAssignee;

    $scope.chart;
    $scope.line = "line";
    $scope.bar = "bar";
    $scope.radar = "radar";
    $scope.doughnut = "doughnut";
    $scope.pie = "pie";
    $scope.horizontalBar = "horizontalBar";

    $scope.title = "Analytics Controller";
    $scope.rawData = rawDataService;

    // First Chart, Bar Chart
    DataService.getCasesVSCategory().then(function(res){
        $scope.labelsCategory = res[0];
        $scope.dataCategory = res[1];
        $scope.optionsCategory = dataOptions("Cases per Cateogry");
        $scope.colorsCategory = [
            "#E1F5FE", "#B3E5FC", "#81D4FA",
            "#4FC3F7", "#29B6F6", "#03A9F4",
            "#039BE5", "#0288D1", "#0277BD"
        ];
    });
    // Second Chart, Bar Chart
    DataService.getCasesVSAssignee().then(function(res){
        $scope.labelsAssignee = res[0];
        $scope.dataAssignee = res[1];
        $scope.optionsAssignee = dataOptions("Cases per Assignee");
        $scope.colorsAssignee = [
            "#E0F2F1", "#B2DFDB", "#80CBC4",
            "#4DB6AC", "#26A69A", "#009688",
            "#00897B", "#00796B", "#00695C"
        ];
    });
    // Third Chart, Time Series
    DataService.getCasesVSTime().then(function(res){
        $scope.labelsDate = res[0];
        $scope.dataDate = res[1];
        $scope.optionsDate = dataOptions("Cases vs Time");
        $scope.colorsAssignee = [
            "#E0F2F1", "#B2DFDB", "#80CBC4",
            "#4DB6AC", "#26A69A", "#009688",
            "#00897B", "#00796B", "#00695C"
        ];
    });
    // Fourth Chart, Doughnut
    DataService.getCasesVSRegion().then(function(res){
        $scope.labelsRegion = res[0];
        $scope.dataRegion = res[1];
        $scope.emailsRegion = dataOptions("Cases per Region");
        $scope.colorsRegion = [
            "#C8E6C9", "#A5D6A7", "#81C784",
            "#66BB6A", "#4CAF50", "#43A047",
            "#388E3C", "#2E7D32", "#1B5E20"
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

app.controller("EmailUsController", function($scope, $location, $http, rawDataService, anchorSmoothScroll) {
    $scope.submitEmail = function(subject, content) {
        if (subject && content) {
            $http.post("/submit", {
                subject: subject,
                content: content
            }).success(function(response){
                this.subject = "";
                this.content = "";
            });
        }
    }
});

app.controller("TicketsController", function($scope, $location, $http, rawDataService, anchorSmoothScroll) {
    $scope.rawData = rawDataService;
    $scope.allCategories = findAllCategories(rawDataService);
    $scope.notHidden = false;
    $scope.leftPaneCaseID;
    $scope.rightPaneCaseID;
    $scope.changeBool = function(row, id) {
        console.log("Row: " + JSON.stringify(row, null, 4));
        console.log("ID: " + id);
        $scope.rightPaneCaseID = id;
        // Right panel opens or close, depending on which button is clicked
        if ($scope.notHidden === false) {
            $scope.notHidden = true
        } else {
            $scope.notHidden = false;
        }
    }
    $scope.modifyCategory = function(modCat, id){
        console.log(id);
        console.log(modCat);
        if(modCat && id){
            // // (REMOVE COMMENT LINE 88-92) Talk to Hemanth on how to send this.
            // // Sends
            // $http.post("", {
            //     Category: modCat,
            //     CaseID: id
            // });
        }
    }
});

// User Defined Functions
function rawTransObj(arr, key) {
    var transObj = {};
    arr.forEach(function(row) {
        if (!transObj[row[key]]) {
            transObj[row[key]] = 1;
        } else {
            transObj[row[key]] += 1;
        }
    })
    return transObj;
}

function asArr(obj, keyOrVal) {
    var retArr = [];
    for (var key in obj) {
        if (keyOrVal === "key") {
            retArr.push(key);
        } else if (keyOrVal === "value") {
            retArr.push(obj[key]);
        }
    }
    return retArr;
}

function circleOptions(titleText) {
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

function dataOptions(titleText) {
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
                    position: "left",
                    ticks: {
                        beginAtZero: true,
                        callback: function (value) { if (Number.isInteger(value)) { return value; } },
                        stepSize: 1
                    }
                },
                {
                    id: "y-axis-2",
                    type: "linear",
                    display: false,
                    position: "right",
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
