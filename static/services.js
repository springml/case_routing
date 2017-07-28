app.service('DataService', function($http){
    return {
        getCasesVSCategory: function(){
            return $http.post('/getCaseDetailsVSCategory').then(function(response){
                return response.data.categories;
            });
        },
        getCasesVSAssignee: function(){
            return $http.post('/getCaseDetailsVSAssignee').then(function(response){
                return response.data.assignees;
            });
        },
        getCasesVSTime: function(){
            return $http.post('/getCaseDetailsVSTime').then(function(response){
                return response.data.time;
            });
        },
        getCasesVSRegion: function(){
            return $http.post('/getCaseDetailsVSRegion').then(function(response){
                return response.data.regions;
            });
       },
        getCasesVSRegionAndPriority: function(){
            return $http.post('/getCaseDetailsVSRegionAndPriority').then(function(response){
                return response.data.allColumns;
            });
       },
        getAllData: function(){
            return $http.post('/getAllData').then(function(response){
                var returnArr = []
                function templateObj(CaseID, Subject, Body, Priority, Category, Created_Date, Close_Date, Region, Assignee, Status){
                    return {
                        CaseID: CaseID,
                        Subject: Subject,
                        Body: Body,
                        Priority: Priority,
                        Category: Category,
                        Created_Date: Created_Date,
                        Close_Date: Close_Date,
                        Region: Region,
                        Assignee: Assignee,
                        Status: Status
                    }
                }

                response.data.allColumns.forEach(function(row){
                    returnArr.push(templateObj(row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9]));
                });
                return returnArr;
            });
        }
    }
});

app.service('anchorSmoothScroll', function() {
    this.scrollTo = function(eID) {

        var startY = currentYPosition();
        var stopY = elmYPosition(eID);
        var distance = stopY > startY ? stopY - startY : startY - stopY;
        if (distance < 100) {
            scrollTo(0, stopY);
            return;
        }
        var speed = Math.round(distance / 100);
        if (speed >= 20) speed = 20;
        var step = Math.round(distance / 25);
        var leapY = stopY > startY ? startY + step : startY - step;
        var timer = 0;
        if (stopY > startY) {
            for (var i = startY; i < stopY; i += step) {
                setTimeout("window.scrollTo(0, " + leapY + ")", timer * speed);
                leapY += step;
                if (leapY > stopY) leapY = stopY;
                timer++;
            }
            return;
        }
        for (var i = startY; i > stopY; i -= step) {
            setTimeout("window.scrollTo(0, " + leapY + ")", timer * speed);
            leapY -= step;
            if (leapY < stopY) leapY = stopY;
            timer++;
        }
        function currentYPosition() {
            // Firefox, Chrome, Opera, Safari
            if (self.pageYOffset) return self.pageYOffset;
            // Internet Explorer 6 - standards mode
            if (document.documentElement && document.documentElement.scrollTop)
                return document.documentElement.scrollTop;
            // Internet Explorer 6, 7 and 8
            if (document.body.scrollTop) return document.body.scrollTop;
            return 0;
        }
        function elmYPosition(eID) {
            var elm = document.getElementById(eID);
            var y = elm.offsetTop;
            var node = elm;
            while (node.offsetParent && node.offsetParent != document.body) {
                node = node.offsetParent;
                y += node.offsetTop;
            }
            return y;
        }
    };
});
