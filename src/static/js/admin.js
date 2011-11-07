Admin = function() {
    function init(tabIndex)
    {
        $("#admin_sections").tabs();
        $(".date").datepicker({dateFormat: 'mm/dd/yy', constrainInput: true, minDate: 0});
        $("#fileVaultUsageBar").progressbar({value:0});
        $("#currentUsersBox").dialog($.extend({
            title: "<span class='group'>Current Filelocker Users</span>"
        }, Defaults.smallDialog));
        $("#userCreateBox").dialog($.extend({
            title: "<span class='user_new'>Create New User</span>"
        }, Defaults.smallDialog));
        $("#userUpdateBox").dialog($.extend({
            title: "<span class='edit'>Update User</span>" //TODO which user?
        }, Defaults.smallDialog));
        $("#userHistoryBox").dialog($.extend({
            title: "<span class='clock'>View History for User</span>", //TODO which user?
            close: function() { $("#userHistoryCurrentUser").val(""); }
        }, Defaults.largeDialog));
        $("#attributeCreateBox").dialog($.extend({
            title: "<span class='attribute_new'>Create New Attribute</span>"
        }, Defaults.smallDialog));
        $("#userUpdatePermissionsBox").dialog($.extend({
            title: "<span class='wand'>Edit Permissions</span>"
        }, Defaults.smallDialog));
        $("#systemStatisticsBox").dialog($.extend({
            title: "<span class='statistics'>View System Usage Statistics</span>"
        }, Defaults.largeDialog));
        $("#updatePasswordBox").dialog($.extend({
            title: "<span class='statistics'>Update Password</span>"
        }, Defaults.smallDialog));
        $("#adminLink").removeClass("loading");
        $("#adminLink").addClass("settings");
        if($("#userTable tr").length>0)
        {
            $("#userTableSorter").tablesorter({
                headers: {
                    0: {sorter: false},
                    1: {sorter: 'text'}, 
                    2: {sorter: 'text'},
                    3: {sorter: 'text'},
                    4: {sorter: 'text'},
                    5: {sorter: 'fileSize'},
                    6: {sorter: false}
                },
                sortList: [[1,0]]
            });
            $("#userTableSorter").bind("sortStart",function() {
                $("#userSorterLoading").show();
            }).bind("sortEnd",function() {
                $("#userSorterLoading").hide();
            });
        }
        if($("#attributeTableSorter tr").length>2) // Accounts for header and dotted line row
        {
            $("#attributeTableSorter").tablesorter({
                headers: {
                    0: {sorter: false},
                    1: {sorter: 'text'}, 
                    2: {sorter: 'text'}
                },
                sortList: [[1,0]]
            });
        }
        else
            $("#attributeTableSorter").append("<tr class='oddRow'><td></td><td><i>No attributes.</i></td><td></td></tr>");
        $("#currentUsersTableSorter").tablesorter({
            headers: {
                0: {sorter: false},
                1: {sorter: 'text'},
                2: {sorter: 'text'}
            },
            sortList: [[1,0]]
        });
        if (tabIndex !== null)
            $("#admin_sections").tabs("select", tabIndex);
        $("#adminBackLink").html("<div class='back'><a href='javascript:StatusResponse.hide();javascript:FLFile.load();' title='Take me back to \"My Files\"'>Back</a></div>");
        loadTemplateForEditing();
        getVaultUsage();
    }
    function load(tabIndex)
    {
        $("#adminLink").removeClass("settings");
        $("#adminLink").addClass("loading");
        $("#wrapper_2col").load(FILELOCKER_ROOT+"/admin?format=text&ms=" + new Date().getTime(), {}, function (responseText, textStatus, xhr) {
            if (textStatus == "error")
                StatusResponse.create("loading admin interface", "Error "+xhr.status+": "+xhr.textStatus, false);
            else 
            {
                if ($("#sessionState").length >0 && $("#sessionState").val() == "expired")
                    Filelocker.login();
                else
                    init(tabIndex);
            }
            Utility.tipsyfy();
            $("#userTableSorterWrapper").scroll(function(){
                if ($(this)[0].scrollHeight - $(this).scrollTop() == $(this).outerHeight()) {
                    User.load();
                }
            });
        });
    }
    function getVaultUsage()
    {
        Filelocker.request("/admin/get_vault_usage", "retrieving vault usage", {}, true, function(returnData) {
            if (returnData.data !== undefined)
            {
                var percentFull = parseInt(parseFloat(returnData.data.vaultUsedMB) / parseFloat(returnData.data.vaultCapacityMB) * 100, 10);
                $("#fileVaultUsageBar").progressbar("value", percentFull);
                $("#fileVaultUsageBar").attr("title", (returnData.data.vaultUsedMB / 1024).toFixed(2) + " GB used out of " + (returnData.data.vaultCapacityMB / 1024).toFixed(2) + " GB");
            }
        });
    }
    function updateConfig()
    {
        var values = {};
        $('#configForm :input').each(function() {
            values[this.name] = $(this).val();
        });
        Filelocker.request("/admin/update_server_config", "updating config", values, true, function() {
            load(3);
        });
    }
    
    User = function() {
        function load(length)
        {
            $("#userSorterLoading").show();
            var data = {
                start: $("#userTable tr").length,
                length: length || 50
            };
            Filelocker.request("/admin/get_all_users", "loading users", data, false, function(returnData) {
                var html = "";
                $.each(returnData.data, function() {
                    html += "<tr id='user_"+this.userId+"' class='userRow'>";
                    html += "<td id='userNameElement_"+this.userId+"' class='userNameElement'><input type='checkbox' name='select_user' value='"+this.userId+"' class='userSelectBox' id='checkbox_"+this.userId+"'>";
                    html += "<div class='posrel'>";
                    html += "<div id='menu_row_"+this.userId+"' class='menuUsers hidden'>";
                    html += "<ul class='menu'>";
                    html += "<li><div class='button' style='width: 185px;'><a href='javascript:promptUpdateUser(\""+this.userId+"\", \""+this.userFirstName+"\", \""+this.userLastName+"\", \""+this.userEmail+"\", "+this.userQuota+", "+this.isRole.toString()+");' title='Edit user account for \""+this.userId+"\"' class='editButton'><span><center>Edit Account</center></span></a></div></li>";
                    html += "<li><div class='button' style='width: 185px;'><a href='javascript:promptUpdatePermissions(\""+this.userId+"\");' title='Grant and revoke user permissions for \""+this.userId+"\"' class='wandButton'><span><center>Edit Permissions</center></span></a></div></li>";
                    html += "</ul>";
                    html += "</div>";
                    html += "</td>";
                    if(this.isAdmin)
                        html += "<td><a href='javascript:promptViewUserHistory(\""+this.userId+"\");' class='admin' title='View Filelocker interactions for \""+this.userId+"\" (admin)'>"+this.userId+"</a></td>";
                    else
                        html += "<td><a href='javascript:promptViewUserHistory(\""+this.userId+"\");' class='clock' title='View Filelocker interactions for \""+this.userId+"\"'>"+this.userId+"</a></td>";
                    html += "<td onClick='userRowClick(\""+this.userId+"\")'>"+this.userLastName+"</td>";
                    html += "<td onClick='userRowClick(\""+this.userId+"\")'>"+this.userFirstName+"</td>";
                    html += "<td onClick='userRowClick(\""+this.userId+"\")'>"+this.userEmail+"</td>";

                    var percentUsed = 0;
                    var quotaUsedMB = Math.round(parseFloat(this.userQuotaUsed));
                    if(parseInt(this.userQuota) > 0)
                        percentUsed = Math.round(parseFloat(this.userQuotaUsed)/parseFloat(this.userQuota)*100)
                    if(parseInt(this.userQuota) >= 1024)
                        html += "<td onClick='userRowClick(\""+this.userId+"\")'><span class='userQuotaUsage pseudoLink' title='"+percentUsed+"% ("+quotaUsedMB+" MB) used'>"+Math.round(parseFloat(this.userQuota)/1024).toFixed(1)+" GB</span></td>";
                    else
                        html += "<td onClick='userRowClick(\""+this.userId+"\")'><span class='userQuotaUsage pseudoLink' title='"+percentUsed+"% ("+quotaUsedMB+" MB) used'>"+this.userQuota+" MB</span></td>";
                    html += "<td onClick='userRowClick(\""+this.userId+"\")' class='dropdownArrowNarrow rightborder'></td>";
                    html += "</tr>";
                });
                $("#userTable").append(html);
                $("#userTableSorter").trigger("update");
                $("#userTableSorter").trigger("applyWidgets");
                Utility.tipsyfy();
                $("#usersLoadedNow").html($("#userTable tr").length);
                $("#userSorterLoading").hide();
            });
        }
        function create()
        {
            if($("#createUserId").val() === "")
                StatusResponse.create("creating user", "New user must have a user ID.", false);
            else if($("#createUserFirstName").val() === "" && $("#createUserLastName").val() === "")
                StatusResponse.create("creating user", "New user must have a name.", false);
            else if($("#createUserQuota").val() === "")
                StatusResponse.create("creating user", "New user must have a quota.", false);
            else if($("#createUserPassword").val() !== $("#createUserPasswordConfirm").val())
                StatusResponse.create("creating user", "Passwords do not match.", false);
            else
            {
                $("#userCreateBox").dialog("close");
                var data = {
                    userId: $("#createUserId").val(),
                    quota: $("#createUserQuota").val(),
                    firstName: $("#createUserFirstName").val(),
                    lastName: $("#createUserLastName").val(),
                    email: $("#createUserEmail").val(),
                    password: $("#createUserPassword").val(),
                    //confirmPassword: $("#createUserPasswordConfirm").val(),
                    isRole: $("#createUserRole").prop("checked")
                };
                Filelocker.request("/admin/create_user", "creating user", data, true, function() {
                    load(0);
                });
            }
        }
        function update()
        {
            var data = {
                userId: $("#updateUserId").val(),
                quota: $("#updateUserQuota").val(),
                email: $("#updateUserEmail").val(),
                firstName: $("#updateUserFirstName").val(),
                lastName: $("#updateUserLastName").val(),
                password: $("#updateUserPassword").val(),
                confirmPassword: $("#updateUserConfirmPassword").val(),
                isRole: $("#updateUserRole").prop("checked")
            };
            Filelocker.request("/admin/update_user", "updating user", data, true, function() {
                $("#userUpdateBox").dialog("close");
                load(0);
            });
        }
        function del() 
        {
            var action = "deleting users";
            var userIds = "";
            $("#userTable :checked").each(function() { userIds += $(this).val()+","; });
            if(userIds !== "")
            {
                Filelocker.request("/admin/delete_users", action, {userIds:userIds}, true, function() {
                    load(0);
                });
            }
            else
                StatusResponse.create("deleting users", "Select user(s) for deletion.", false);
        }
        function promptCreate()
        {
            $("#createUserId").val("");
            $("#createUserFirstName").val("");
            $("#createUserLastName").val("");
            $("#createUserQuota").val("");
            $("#createUserEmail").val("");
            $("#createUserPassword").val("");
            $("#createUserPasswordConfirm").val("");
            $("#bulkCreateUserQuota").val("");
            $("#bulkCreateUserPassword").val("");
            $("#bulkCreateUserPasswordConfirm").val("");
            $("#bulkCreateUserPermissions").empty();
            Filelocker.request("/admin/get_user_permissions", "retrieving user permissions", {}, false, function(returnData)
            {
                for (var i=0;i<returnData.data.length;i++)
                {
                    $("#bulkCreateUserPermissions").append("<input type='checkbox' value='"+returnData.data[i].permissionId+"' id='bulkCreateCheckbox_"+i+"' name='select_permission' class='permissionSelectBox' /><span onClick='javascript:check(\"bulkCreateCheckbox_"+i+"\")'>" + returnData.data[i].permissionName + "</span><br />");
                }
                $("#userCreateTabs").tabs();
                $("#userCreateBox").dialog("open");
            });
        }
        function promptUpdate(userId, firstName, lastName, email, quota)
        {
            $("#updateUserFirstName").val(firstName);
            $("#updateUserLastName").val(lastName);
            $("#updateUserEmail").val(email);
            $("#updateUserQuota").val(quota);
            $("#updateUserId").val(userId);
            $("#userUpdateBox").dialog("open");
        }
        function promptViewHistory(userId)
        {
            $("#userHistory").empty();
            $("#userHistoryCurrentUser").val(userId);
            var data = {
                userId:userId,
                startDate:$("#userHistoryStartDate").val(),
                endDate:$("#userHistoryEndDate").val()
            }
            Filelocker.request("/history", "loading user history", data, false, function(returnData) {
                $.each(returnData.data, function() {
                    $("#userHistory").append("<tr><td>"+this.actionDatetime+"</td><td class='"+this.displayClass+"'>"+this.action+"</td><td>"+this.message+"</td></tr>");
                });
                if($("#userHistory").html() === "")
                    $("#userHistory").append("<tr><td colspan='3'><i>This user has no history of interactions with Filelocker.</i></td></tr>");
                $("#userHistoryTableSorter").tablesorter({
                    headers: {
                        0: {sorter: 'shortDate'},
                        1: {sorter: 'text'},
                        2: {sorter: 'text'}
                    }
                });
                $("#userHistoryBox").dialog("open");
                $("#userHistoryTableSorter").trigger("update");
                $("#userHistoryTableSorter").trigger("sorton",[[[0,0]]]);
            });
        }
        function rowClick(userId)
        {
            $(".menuUsers").each(function(index) { $(this).addClass("hidden");}); // Hide other menus
            if($("#user_"+userId).hasClass("rowSelected"))
            {
                $(".userRow").each(function(index) { $(this).removeClass("rowSelected");}); // Deselects other rows
                $("#user_"+userId).removeClass("rowSelected"); // Select the row of the file
                $("#userNameElement_"+userId).removeClass("leftborder");
                $("#menu_row_"+userId).addClass("hidden"); // Show the menu on the selected file
            }
            else
            {
                $(".userRow").each(function(index) { $(this).removeClass("rowSelected");}); // Deselects other rows
                $("#user_"+userId).addClass("rowSelected"); // Select the row of the file
                $("#userNameElement_"+userId).addClass("leftborder");
                $("#menu_row_"+userId).removeClass("hidden"); // Show the menu on the selected file
            }
        }
        function selectAll()
        {
            $(".userSelectBox").prop("checked", $("#allUsersCheckbox").prop("checked"));
        }
        function showCurrent() { $("#currentUsersBox").dialog("open"); }

        return {
            load:load,
            create:create,
            update:update,
            del:del,
            propmtCreate:promptCreate,
            promptUpdate:promptUpdate,
            promptViewHistory:promptViewHistory,
            rowClick:rowClick,
            selectAll:selectAll,
            showCurrent:showCurrent
        };
    }();
    
    Attribute = function() {
        function create()
        {
            var data = {
                attributeId: $("#createAttributeId").val(),
                attributeName: $("#createAttributeName").val()
            };
            Filelocker.request("/admin/create_attribute", "creating attribute", data, true, function() {
                $("#attributeCreateBox").dialog("close");
                load(2);
            });
        }
        function del()
        {
            var action = "deleting attribute";
            var attributeIds = "";
            $("#attributeTable :checked").each(function() { attributeIds += $(this).val()+","; });
            if(attributeIds !== "")
            {
                Filelocker.request("/admin/delete_attributes", action, {attributeIds: attributeIds}, true, function() {
                    load(2);
                });
            }
            else
                StatusResponse.create(action, "Select attribute(s) for deletion.", false);
        }
        function promptCreate()
        {
            $("#attributeCreateBox").dialog("open");
        }

        return {
            create:create,
            del:del,
            promptCreate:promptCreate
        };
    }();

    Permission = function() {
        function load(userId)
        {
            Filelocker.request("/admin/get_user_permissions", "loading permissions", {userId: userId}, false, function(returnData) {
                $("#permissionsTable").empty();
                for (var i=0;i<returnData.data.length;i++)
                {
                    //TODO clean this up...
                    var checkedStatus = "";
                    var disabled = "";
                    if (returnData.data[i].inheritedFrom !== "")
                    {
                        checkedStatus = "checked";
                        if (returnData.data[i].inheritedFrom.substr(0, 7) == "(group)")
                            disabled = "disabled";
                    }
                    var permRow = returnData.data[i];
                    $("#permissionsTable").append("<tr id='permission_"+permRow.permissionId+"' class='fileRow'><td><input type='checkbox' value='"+permRow.permissionId+"' id='checkbox_"+i+"' name='select_permission' class='permissionSelectBox' onChange=\"permissionChecked('"+userId+"','"+permRow.permissionId+"', "+i+")\""+checkedStatus+" "+disabled+"/>"+permRow.permissionId+"</td><td>"+permRow.permissionName+"</td><td>"+permRow.inheritedFrom+"</td></tr>");
                }
                $("#userPermissionTableSorter").tablesorter({
                    headers: {
                        0: {sorter: 'text'},
                        1: {sorter: 'text'},
                        2: {sorter: 'text'}
                    }
                });
                $("#userPermissionTableSorter").trigger("update");
                $("#userPermissionTableSorter").trigger("sorton",[[[0,0]]]);
                $("#userUpdatePermissionsBox").dialog("open");
            });
        }
        function grant(data)
        {
            Filelocker.request("/admin/grant_user_permission", "granting permission", data, true, function() {
                load(data.userId);
            });
        }
        function revoke(data)
        {
            Filelocker.request("/admin/revoke_user_permission", "revoking permission", data, true, function() {
                load(data.userId);
            });
        }
        function changed(userId, permissionId, rowId)
        {
            var data = {
                userId: userId,
                permissionId: permissionId
            };
            if ($("#checkbox_"+rowId).prop("checked"))
                grant(data);
            else
                revoke(data);
        }

        return {
            load:load,
            changed:changed
        };
    }();

    Template = function() {
        function load()
        {
            if ($('#template_selector').val() !== "")
            {
                Filelocker.request("/admin/get_template", "loading template", {templateName:$('#template_selector').val()}, true, function(returnData) {
                    $("#templateEditArea").val(returnData.data);
                });
            }
        }
        function create()
        {
            var data = {
                templateName: $("#template_selector").val(),
                templateText: $("#templateEditArea").val()
            };
            Filelocker.request("/admin/create_template", "creating custom template", data, true, function(returnData) {
                $("#templateEditArea").val(returnData.data);
            });
        }

        function revert()
        {
            var data = {
                templateName: $("#template_selector").val(),
                templateText: $("#templateEditArea").val()
            };
            Filelocker.request("/admin/revert_template", "reverting custom template", data, true, function(returnData) {
                $("#templateEditArea").val(returnData.data);
            });
        }
        return {
            load:load,
            create:create,
            revert:revert
        };
    }();

//    Statistics = function() {
//    function showStatistics()
//    {
//        getHourlyStatistics();
//        getDailyStatistics();
//        getMonthlyStatistics();
//        $("#systemStatistics").tabs();
//        setTimeout(function(){ $("#systemStatisticsBox").dialog("open"); }, 300);
//    }
//    function getHourlyStatistics()
//    {
//        $("#hourly").empty();
//        $.post(FILELOCKER_ROOT+'/file/get_hourly_statistics?format=json&ms=' + new Date().getTime(), {},
//        function(returnData) {
//            var hourlyTable = "<div class='statisticsTableWrapper'><table id='hourlyStatisticsTable' class='statisticsTable'><colgroup><col class='colHead' /></colgroup><caption>% of Total Usage by Hour (Last 30 Days)</caption><thead><tr><td class='rowHead'>Hour</td>";
//            var hourlyHeaders = "";
//            var hourlyDownloadData = "";
//            var hourlyUploadData = "";
//            for (var i=0; i<24; i++)
//            {
//                hourlyHeaders += "<th scope='col'>"+i+"</th>";
//                var hasDownloadData = false;
//                var hasUploadData = false;
//                $.each(returnData.data.downloads, function(key, value) {
//                    if (key == i)
//                    {
//                        hourlyDownloadData += "<td scope='row'>"+value+"</td>";
//                        hasDownloadData = true;
//                        return false;
//                    }
//                });
//                $.each(returnData.data.uploads, function(key, value) {
//                    if (key == i)
//                    {
//                        hourlyUploadData += "<td scope='row'>"+value+"</td>";
//                        hasUploadData = true;
//                        return false;
//                    }
//                });
//                if (!hasDownloadData)
//                    hourlyDownloadData += "<td scope='row'>0</td>";
//                if (!hasUploadData)
//                    hourlyUploadData += "<td scope='row'>0</td>";
//            }
//            hourlyTable += hourlyHeaders + "</tr></thead><tbody><tr><th scope='row' class='rowHead'>Downloads</th>" + hourlyDownloadData + "</tr>";
//            hourlyTable += "<tr><th scope='row' class='rowHead'>Uploads</th>" + hourlyUploadData + "</tr>";
//            hourlyTable += "</tbody></table></div>";
//            $("#hourly").html("<div>" + hourlyTable + "</div><br />");
//            if(!!document.createElement('canvas').getContext)
//            {
//                $("#hourlyStatisticsTable").visualize({
//                    type: 'line',
//                    width: 600,
//                    height: 200,
//                    appendKey: true,
//                    colors: ['#fee932','#000000'],
//                    diagonalLabels: false,
//                    labelWidth: 10,
//                    yLabelUnit: "%"
//                }).appendTo("#hourly").trigger("visualizeRefresh");
//            }
//            else
//                $("#hourly").append("<i>Your browser does not support the canvas element of HTML5.</i>");
//        }, 'json');
//    }
//    function getDailyStatistics()
//    {
//        $("#daily").empty();
//        $.post(FILELOCKER_ROOT+'/file/get_daily_statistics?format=json&ms=' + new Date().getTime(), {},
//        function(returnData) {
//            var dailyTable = "<div class='statisticsTableWrapper'><table id='dailyStatisticsTable' class='statisticsTable'><colgroup><col class='colHead' /></colgroup><caption>Total Usage by Day (Last 30 Days)</caption><thead><tr><td class='rowHead'>Hour</td>";
//            var dailyHeaders = "";
//            var dailyDownloadData = "";
//            var dailyUploadData = "";
//            var d = new Date();
//            d.setDate(d.getDate()-30);
//            for (var i=0; i<=30; i++)
//            {
//                var dateToUse = d.getMonth()+1+"/"+d.getDate();
//                dailyHeaders += "<th scope='col'>"+dateToUse+"</th>";
//                var hasDownloadData = false;
//                var hasUploadData = false;
//                $.each(returnData.data.downloads, function(key, value) {
//                    if (key == dateToUse)
//                    {
//                        dailyDownloadData += "<td scope='row'>"+value+"</td>";
//                        hasDownloadData = true;
//                        return false;
//                    }
//                });
//                $.each(returnData.data.uploads, function(key, value) {
//                    if (key == dateToUse)
//                    {
//                        dailyUploadData += "<td scope='row'>"+value+"</td>";
//                        hasUploadData = true;
//                        return false;
//                    }
//                });
//                if (!hasDownloadData)
//                    dailyDownloadData += "<td scope='row'>0</td>";
//                if (!hasUploadData)
//                    dailyUploadData += "<td scope='row'>0</td>";
//                d.setDate(d.getDate()+1);
//            }
//            dailyTable += dailyHeaders + "</tr></thead><tbody><tr><th scope='row' class='rowHead'>Downloads</th>" + dailyDownloadData + "</tr>";
//            dailyTable += "<tr><th scope='row' class='rowHead'>Uploads</th>" + dailyUploadData + "</tr>";
//            dailyTable += "</tbody></table></div>";
//            $("#daily").html("<div>" + dailyTable + "</div><br />");
//            if(!!document.createElement('canvas').getContext)
//            {
//                $("#dailyStatisticsTable").visualize({
//                    type: 'line',
//                    width: 600,
//                    height: 200,
//                    appendKey: true,
//                    colors: ['#fee932','#000000'],
//                    diagonalLabels: true,
//                    dottedLast: true,
//                    labelWidth: 10
//                }).appendTo("#daily").trigger("visualizeRefresh");
//            }
//            else
//                $("#daily").append("<i>Your browser does not support the canvas element of HTML5.</i>");
//        }, 'json');
//    }
//    function getMonthlyStatistics()
//    {
//        $("#monthly").empty();
//        $.post(FILELOCKER_ROOT+'/file/get_monthly_statistics?format=json&ms=' + new Date().getTime(), {},
//        function(returnData) {
//            var monthlyTable = "<div class='statisticsTableWrapper'><table id='monthlyStatisticsTable' class='statisticsTable'><colgroup><col class='colHead' /></colgroup><caption>Total Usage by Month (Last 12 Months)</caption><thead><tr><td class='rowHead'>Month</td>";
//            var monthlyHeaders = "";
//            var monthlyDownloadData = "";
//            var monthlyUploadData = "";
//            var months = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}
//            var now = new Date().getMonth()+1;
//            for (var i=1; i<=12; i++)
//            {
//                var month = 0;
//                if (now+i > 12)
//                    month = now+i-12;
//                else
//                    month = now+i;
//                monthlyHeaders += "<th scope='col'>"+months[month]+"</th>";
//                var hasDownloadData = false;
//                var hasUploadData = false;
//                $.each(returnData.data.downloads, function(key, value) {
//                    if (key == month)
//                    {
//                        monthlyDownloadData += "<td scope='row'>"+value+"</td>";
//                        hasDownloadData = true;
//                        return false;
//                    }
//                });
//                $.each(returnData.data.uploads, function(key, value) {
//                    if (key == month)
//                    {
//                        monthlyUploadData += "<td scope='row'>"+value+"</td>";
//                        hasUploadData = true;
//                        return false;
//                    }
//                });
//                if (!hasDownloadData)
//                    monthlyDownloadData += "<td scope='row'>0</td>";
//                if (!hasUploadData)
//                    monthlyUploadData += "<td scope='row'>0</td>";
//            }
//            monthlyTable += monthlyHeaders + "</tr></thead><tbody><tr><th scope='row' class='rowHead'>Downloads</th>" + monthlyDownloadData + "</tr>";
//            monthlyTable += "<tr><th scope='row' class='rowHead'>Uploads</th>" + monthlyUploadData + "</tr>";
//            monthlyTable += "</tbody></table></div>";
//            $("#monthly").html("<div>" + monthlyTable + "</div><br />");
//            if(!!document.createElement('canvas').getContext)
//            {
//                $("#monthlyStatisticsTable").visualize({
//                    type: 'line',
//                    width: 600,
//                    height: 200,
//                    appendKey: true,
//                    colors: ['#fee932','#000000'],
//                    diagonalLabels: false,
//                    dottedLast: true,
//                    labelWidth: 10
//                }).appendTo("#monthly").trigger("visualizeRefresh");
//            }
//            else
//                $("#monthly").append("<i>Your browser does not support the canvas element of HTML5.</i>");
//        }, 'json');
//    }
//  }();
    
    return {
        load:load,
        getVaultUsage:getVaultUsage,
        updateConfig:updateConfig,
        User:User,
        Attribute:Attribute,
        Permission:Permission,
        Template:Template
    }
}();

jQuery(document).ready(function(){
    bulkUserUploader = new qq.FileUploader({
        element: $("#bulkCreateUserUploadButton")[0],
        listElement: $("#bulkCreateUserFileList")[0],
        action: FILELOCKER_ROOT+'/admin/bulk_create_user',
        params: {},
        sizeLimit: 2147483647,
        onSubmit: function(id, fileName){
            if($("#bulkCreateUserPassword").val() == $("#bulkCreateUserPasswordConfirm").val())
            {
                $("#userCreateBox").dialog("close");
                var permissions = "";
                $(".permissionSelectBox:checked").each(function(index) {
                    permissions += $(this).val() + ",";
                });
                bulkUserUploader.setParams({
                    quota: $("#bulkCreateUserQuota").val(),
                    password: $("#bulkCreateUserPassword").val(),
                    permissions: permissions
                });
            }
            else
            {
                StatusResponse.create("creating users", "Passwords do not match.", false);
                return false;
            }
        },
        onComplete: function(id, fileName, response){
            StatusResponse.show(response, "creating users");
            Admin.load(0);
        }
    });
});