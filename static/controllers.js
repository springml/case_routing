app.controller("DashboardController", ['$scope', '$location', '$http', 'DataService', function($scope, $location, $http, DataService) {
    // Initialize Chart variables
    $scope.labelsDate, $scope.dataDate, $scope.optionsDate, $scope.colorsDate;
    $scope.labelsRegionPriority, $scope.dataRegionPriority, $scope.seriesRegionPriority, $scope.optionsRegionPriority;
    $scope.labesCategory, $scope.dataCategory, $scope.optionsCategory, $scope.colorsCategory;
    $scope.labelsAssignee, $scope.dataAssignee, $scope.optionsAssignee, $scope.colorsAssignee;
    $scope.rawData;
    $scope.chart;
    $scope.line = "line";
    $scope.bar = "bar";
    $scope.radar = "radar";
    $scope.doughnut = "doughnut";
    $scope.pie = "pie";
    $scope.horizontalBar = "horizontalBar";

    $scope.title = "Analytics Controller";

    DataService.getAllData().then(function(data){
        $scope.rawData = data;
    });

    // Cases VS. Time
    DataService.getCasesVSTime().then(function(res){
        $scope.labelsDate = res[0];
        $scope.dataDate = res[1];
        $scope.optionsDate = barOptions("Cases vs Time");
        $scope.colorsDate = [
            "#F9FBE7", "#F0F4C3", "#E6EE9C",
            "#DCE775", "#D4E157", "#CDDC39",
            "#C0CA33", "#AFB42B", "#9E9D24"
        ];
    });
    // // Cases Per Region
    // DataService.getCasesVSRegion().then(function(res){
    //     $scope.labelsRegion = res[0];
    //     $scope.dataRegion = res[1];
    //     $scope.optionsRegion = barOptions("Cases per Region");
    //     $scope.colorsRegion = [
    //
    //     ];
    // });
    // Cases Per Region and Priority
    DataService.getCasesVSRegionAndPriority().then(function(res){
        var cleanData = cleanRegionPriorityData(res)
        $scope.labelsRegionPriority = ["West", "Midwest", "South", "Northeast"];
        $scope.dataRegionPriority = [cleanData.P1, cleanData.P2, cleanData.P3];
        $scope.seriesRegionPriority = ["P1", "P2", "P3"]
        $scope.optionsRegionPriority = stackedBarOptions("Cases Per Region and Priority");
        // $scope.colorsRegionPriority = [["#D4E157"], ["#29B6F6"], ["#26A69A"]];
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
            "#00897B", "#00796B", "#00695C",
            "#004D40", "#00392F", "#00231E",
            "#00231E", "#00231E", "#00231E",
            "#00231E", "#00231E", "#00231E"
        ];
    });
    $scope.overrideRegionPriority = [
        {
            backgroundColor: [
                'rgba(244, 67, 54, 0.7)',
                'rgba(244, 67, 54, 0.7)',
                'rgba(244, 67, 54, 0.7)',
                'rgba(244, 67, 54, 0.7)'
            ],
            borderColor : "rgba(220,220,220,1)"
        }, {
            backgroundColor: [
                'rgba(156, 39, 176, 0.7)',
                'rgba(156, 39, 176, 0.7)',
                'rgba(156, 39, 176, 0.7)',
                'rgba(156, 39, 176, 0.7)'
            ],
            borderColor : "rgba(220,220,220,1)"
        }, {
            backgroundColor: [
                'rgba(33, 150, 243, 0.7)',
                'rgba(33, 150, 243, 0.7)',
                'rgba(33, 150, 243, 0.7)',
                'rgba(33, 150, 243, 0.7)'
            ],
            borderColor : "rgba(220,220,220,1)"
        }
    ]
    $scope.showData = function(event) {
        console.log(event);
    }
}]);

app.controller("EmailUsController", ['$scope', '$location', '$http', 'DataService', function($scope, $location, $http) {
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
}]);

app.controller("TicketsController", ['$scope', '$location', '$http', 'DataService', function($scope, $location, $http, DataService) {
    $scope.rawData;
    $scope.allCategories;

    DataService.getAllData().then(function(data){
        $scope.rawData = data;
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
    $scope.moreButton = function(CaseID){
        return CaseID
    }
    $scope.lessButton = function(CaseID){
        return CaseID
    }
}]);
// -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
// User Defined Functions  -- -- -- -- -- -- --
// -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
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
                        stepSize: 10
                    },
                    maxTicksLimit: 11
                }
            ]
        }
    }
}

function stackedBarOptions(titleText) {
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
            xAxes: [{
                stacked: true,
                gridLines: { display: false },
            }],
            yAxes: [{
                stacked: true,
                ticks: {
                    beginAtZero: true,
                    callback: function(value){
                        if (Number.isInteger(value)){
                            return value;
                        }
                    },
                    stepSize: 10,
                    maxTicksLimit: 11
                }
            }]
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
                        stepSize: 10
                    },
                    maxTicksLimit: 11
                }
            ]
        }
    }
}
function cleanRegionPriorityData(arr){
    var result = {P1: [0, 0, 0, 0], P2: [0, 0, 0, 0], P3: [0, 0, 0, 0]};
    arr.forEach(function(point){
        if(point[2] === "West"){
            result[point[1]][0] = point[0];
        } else if(point[2] === "Midwest"){
            result[point[1]][1] = point[0];

        } else if(point[2] === "South"){
            result[point[1]][2] = point[0];

        } else if(point[2] === "Northeast"){
            result[point[1]][3] = point[0];
        }
    });
    return result;
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
