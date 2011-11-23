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
        $("#roleCreateBox").dialog($.extend({
            title: "<span class='user_new'>Create New Role</span>"
        }, Defaults.smallDialog));
        $("#roleUpdateBox").dialog($.extend({
            title: "<span class='edit'>Update Role</span>" //TODO which user?
        }, Defaults.smallDialog));
        $("#attributeCreateBox").dialog($.extend({
            title: "<span class='attribute_new'>Create New Attribute</span>"
        }, Defaults.smallDialog));
        $("#userUpdatePermissionsBox").dialog($.extend({
            title: "<span class='wand'>Edit Permissions</span>"
        }, Defaults.largeDialog));
        $("#roleUpdatePermissionsBox").dialog($.extend({
            title: "<span class='wand'>Edit Permissions</span>"
        }, Defaults.largeDialog));
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
        if($("#roleTable tr").length>0)
        {
            $("#roleTableSorter").tablesorter({
                headers: {
                    0: {sorter: false},
                    1: {sorter: 'text'},
                    2: {sorter: 'text'},
                    3: {sorter: 'text'},
                    4: {sorter: 'fileSize'},
                    5: {sorter: false}
                },
                sortList: [[1,0]]
            });
            $("#roleTableSorter").bind("sortStart",function() {
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
        $("#admin_sections").tabs("select", tabIndex || Defaults.adminUsersTabIndex);
        $("#adminBackLink").html("<div class='back'><a href='javascript:StatusResponse.hide();javascript:FLFile.load();' title='Take me back to \"My Files\"'>Back</a></div>");
        Template.load();
        getVaultUsage();
    }
    function load(tabIndex)
    {
        $("#adminLink").removeClass("settings");
        $("#adminLink").addClass("loading");
        //todo no load
        $("#wrapper_2col").load(FILELOCKER_ROOT+"/admin_console?format=text&ms=" + new Date().getTime(), {}, function (responseText, textStatus, xhr) {
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
        Filelocker.request("/admin/get_vault_usage", "retrieving vault usage", {}, false, function(returnData) {
            if (returnData.data != null)
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
            load(Defaults.adminConfigTabIndex);
        });
    }
    
    User = function() {
        function load(length)
        {
            $("#userSorterLoading").show();
            var data = {
                start: $("#userTable tr").length,
                length: length || 50 //TODO to defaults.
            };
            Filelocker.request("/account/get_all_users", "loading users", data, false, function(returnData) {
                var html = "";
                $.each(returnData.data, function() {
                    html += "<tr id='user_"+this.userId+"' class='userRow'>";
                    html += "<td id='userNameElement_"+this.userId+"' class='userNameElement'><input type='checkbox' name='select_user' value='"+this.userId+"' class='userSelectBox' id='checkbox_"+this.userId+"'>";
                    html += "<div class='posrel'>";
                    html += "<div id='menu_row_"+this.userId+"' class='menuUsers hidden'>";
                    html += "<ul class='menu'>";
                    html += "<li><div class='button' style='width: 185px;'><a href='javascript:Admin.User.promptUpdate(\""+this.userId+"\", \""+this.userFirstName+"\", \""+this.userLastName+"\", \""+this.userEmail+"\", "+this.userQuota+");' title='Edit user account for \""+this.userId+"\"' class='editButton'><span><center>Edit Account</center></span></a></div></li>";
                    html += "<li><div class='button' style='width: 185px;'><a href='javascript:Admin.Permission.load(\""+this.userId+"\");' title='Grant and revoke user permissions for \""+this.userId+"\"' class='wandButton'><span><center>Edit Permissions</center></span></a></div></li>";
                    html += "</ul>";
                    html += "</div>";
                    html += "</td>";
                    if(this.isAdmin)
                        html += "<td><a href='javascript:Admin.User.promptViewHistory(\""+this.userId+"\");' class='admin' title='View Filelocker interactions for \""+this.userId+"\" (admin)'>"+this.userId+"</a></td>";
                    else
                        html += "<td><a href='javascript:Admin.User.promptViewHistory(\""+this.userId+"\");' class='clock' title='View Filelocker interactions for \""+this.userId+"\"'>"+this.userId+"</a></td>";
                    html += "<td onClick='javascript:Admin.User.rowClick(\""+this.userId+"\")'>"+this.userLastName+"</td>";
                    html += "<td onClick='javascript:Admin.User.rowClick(\""+this.userId+"\")'>"+this.userFirstName+"</td>";
                    html += "<td onClick='javascript:Admin.User.rowClick(\""+this.userId+"\")'>"+this.userEmail+"</td>";

                    var percentUsed = 0;
                    var quotaUsedMB = Math.round(parseFloat(this.userQuotaUsed));
                    if(parseInt(this.userQuota) > 0)
                        percentUsed = Math.round(parseFloat(this.userQuotaUsed)/parseFloat(this.userQuota)*100)
                    if(parseInt(this.userQuota) >= 1024)
                        html += "<td onClick='javascript:Admin.User.rowClick(\""+this.userId+"\")'><span class='userQuotaUsage pseudoLink' title='"+percentUsed+"% ("+quotaUsedMB+" MB) used'>"+Math.round(parseFloat(this.userQuota)/1024).toFixed(1)+" GB</span></td>";
                    else
                        html += "<td onClick='javascript:Admin.User.rowClick(\""+this.userId+"\")'><span class='userQuotaUsage pseudoLink' title='"+percentUsed+"% ("+quotaUsedMB+" MB) used'>"+this.userQuota+" MB</span></td>";
                    html += "<td onClick='javascript:Admin.User.rowClick(\""+this.userId+"\")' class='dropdownArrowNarrow rightborder'></td>";
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
                    confirmPassword: $("#createUserPasswordConfirm").val()
                };
                Filelocker.request("/account/create_user", "creating user", data, true, function() {
                    Admin.load(Defaults.adminUsersTabIndex);
                });
            }
        }
        function update()
        {
            var data = {
                userId: $("#updateUserId").val(),
                quota: $("#updateUserQuota").val(),
                firstName: $("#updateUserFirstName").val(),
                lastName: $("#updateUserLastName").val(),
                email: $("#updateUserEmail").val(),
                password: $("#updateUserPassword").val(),
                confirmPassword: $("#updateUserConfirmPassword").val()
            };
            Filelocker.request("/account/update_user", "updating user", data, true, function() {
                $("#userUpdateBox").dialog("close");
                Admin.load(Defaults.adminUsersTabIndex);
            });
        }
        function del() 
        {
            var action = "deleting users";
            var userIds = "";
            $("#userTable :checked").each(function() { userIds += $(this).val()+","; });
            if(userIds !== "")
            {
                Filelocker.request("/account/delete_users", action, {userIds:userIds}, true, function() {
                    Admin.load(Defaults.adminUsersTabIndex);
                });
            }
            else
                StatusResponse.create(action, "Select user(s) for deletion.", false);
        }
        function promptCreate()
        {
            $("#createUserId").val("");
            $("#createUserFirstName").val("");
            $("#createUserLastName").val("");
            $("#createUserEmail").val("");
            $("#createUserPassword").val("");
            $("#createUserPasswordConfirm").val("");
            $("#bulkCreateUserQuota").val("");
            $("#bulkCreateUserPassword").val("");
            $("#bulkCreateUserPasswordConfirm").val("");
            $("#bulkCreateUserPermissions").empty();
            Filelocker.request("/account/get_permissions", "retrieving user permissions", {}, false, function(returnData)
            {
                $.each(returnData.data, function(index, value) {
                    $("#bulkCreateUserPermissions").append("<input type='checkbox' value='"+value.permissionId+"' id='bulkCreateCheckbox_"+index+"' name='select_permission' class='permissionSelectBox' /><span onClick='javascript:check(\"bulkCreateCheckbox_"+index+"\")'>" + value.permissionName + "</span><br />");
                });
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
            promptCreate:promptCreate,
            promptUpdate:promptUpdate,
            promptViewHistory:promptViewHistory,
            rowClick:rowClick,
            selectAll:selectAll,
            showCurrent:showCurrent
        };
    }();

    Role = function() {
        function load(length)
        {
            $("#roleSorterLoading").show();
            var data = {
                start: $("#roleTable tr").length,
                length: length || 50 //TODO to defaults.
            };
            Filelocker.request("/account/get_all_roles", "loading roles", data, false, function(returnData) {
                var html = "";
                $.each(returnData.data, function() {
                    html += "<tr id='role_"+this.roleId+"' class='roleRow'>";
                    html += "<td id='roleNameElement_"+this.roleId+"' class='roleNameElement'><input type='checkbox' name='select_role' value='"+this.roleId+"' class='roleSelectBox' id='checkbox_"+this.roleId+"'>";
                    html += "<div class='posrel'>";
                    html += "<div id='menu_row_"+this.roleId+"' class='menuRoles hidden'>";
                    html += "<ul class='menu'>";
                    html += "<li><div class='button' style='width: 185px;'><a href='javascript:Admin.Role.promptUpdate(\""+this.roleId+"\", \""+this.roleFirstName+"\", \""+this.roleLastName+"\", \""+this.roleEmail+"\", "+this.roleQuota+", "+this.isRole.toString()+");' title='Edit role account for \""+this.roleId+"\"' class='editButton'><span><center>Edit Account</center></span></a></div></li>";
                    html += "<li><div class='button' style='width: 185px;'><a href='javascript:Admin.RolePermission.load(\""+this.roleId+"\");' title='Grant and revoke role permissions for \""+this.roleId+"\"' class='wandButton'><span><center>Edit Permissions</center></span></a></div></li>";
                    html += "</ul>";
                    html += "</div>";
                    html += "</td>";
                    html += "<td onClick='javascript:Admin.Role.rowClick(\""+this.roleId+"\");'><span class='role'>"+this.roleId+"</span></td>";
                    html += "<td onClick='javascript:Admin.Role.rowClick(\""+this.roleId+"\");'>"+this.roleLastName+"</td>";
                    html += "<td onClick='javascript:Admin.Role.rowClick(\""+this.roleId+"\");'>"+this.roleFirstName+"</td>";
                    html += "<td onClick='javascript:Admin.Role.rowClick(\""+this.roleId+"\");'>"+this.roleEmail+"</td>";

                    var percentUsed = 0;
                    var quotaUsedMB = Math.round(parseFloat(this.roleQuotaUsed));
                    if(parseInt(this.roleQuota) > 0)
                        percentUsed = Math.round(parseFloat(this.roleQuotaUsed)/parseFloat(this.roleQuota)*100)
                    if(parseInt(this.roleQuota) >= 1024)
                        html += "<td onClick='javascript:Admin.Role.rowClick(\""+this.roleId+"\")'><span class='roleQuotaUsage pseudoLink' title='"+percentUsed+"% ("+quotaUsedMB+" MB) used'>"+Math.round(parseFloat(this.roleQuota)/1024).toFixed(1)+" GB</span></td>";
                    else
                        html += "<td onClick='javascript:Admin.Role.rowClick(\""+this.roleId+"\")'><span class='roleQuotaUsage pseudoLink' title='"+percentUsed+"% ("+quotaUsedMB+" MB) used'>"+this.roleQuota+" MB</span></td>";
                    html += "<td onClick='javascript:Admin.Role.rowClick(\""+this.roleId+"\")' class='dropdownArrowNarrow rightborder'></td>";
                    html += "</tr>";
                });
                $("#roleTable").append(html);
                $("#roleTableSorter").trigger("update");
                $("#roleTableSorter").trigger("applyWidgets");
                Utility.tipsyfy();
                $("#rolesLoadedNow").html($("#roleTable tr").length);
                $("#roleSorterLoading").hide();
            });
        }
        function create()
        {
            if($("#createRoleId").val() === "")
                StatusResponse.create("creating role", "New role must have a role ID.", false);
            else if($("#createRoleName").val() === "")
                StatusResponse.create("creating role", "New role must have a name.", false);
            else if($("#createRoleQuota").val() === "")
                StatusResponse.create("creating role", "New role must have a quota.", false);
            else
            {
                var data = {
                    roleId: $("#createRoleId").val(),
                    quota: $("#createRoleQuota").val(),
                    roleName: $("#createRoleName").val(),
                    email: $("#createRoleEmail").val()
                };
                Filelocker.request("/account/create_role", "creating role", data, true, function() {
                    $("#roleCreateBox").dialog("close");
                    Admin.load(Defaults.adminRolesTabIndex);
                });
            }
        }
        function update()
        {
            var data = {
                roleId: $("#updateRoleId").val(),
                quota: $("#updateRoleQuota").val(),
                roleName: $("#updateRoleName").val(),
                email: $("#updateRoleEmail").val()
            };
            Filelocker.request("/account/update_role", "updating role", data, true, function() {
                $("#roleUpdateBox").dialog("close");
                Admin.load(Defaults.adminRolesTabIndex);
            });
        }
        function del()
        {
            var action = "deleting roles";
            var roleIds = "";
            $("#roleTable :checked").each(function() { roleIds += $(this).val()+","; });
            if(roleIds !== "")
            {
                Filelocker.request("/account/delete_roles", action, {roleIds:roleIds}, true, function() {
                    Admin.load(Defaults.adminRolesTabIndex);
                });
            }
            else
                StatusResponse.create(action, "Select role(s) for deletion.", false);
        }
        function prompt(roleId)
        {
            $("#viewRoleBox").load(FILELOCKER_ROOT+"/account/get_role_members?format=searchbox_html&ms=" + new Date().getTime(), {roleId: roleId}, function (responseText, textStatus, xhr) {
                if (textStatus == "error")
                    StatusResponse.create("loading role membership", "Error "+xhr.status+": "+xhr.textStatus, false);
                else {
                    if ($("#sessionState").length >0 && $("#sessionState").val() == "expired")
                        Filelocker.login();
                    else
                    {
                        $("#viewRoleBox").dialog($.extend({
                            title: "<span class='view'>View Role Membership</span>"
                        }, Defaults.largeDialog));
                        $("#current_role_members").accordion({ autoHeight: false });
                        Account.Search.init("manage_roles");
                        $("#viewRoleBox").dialog("open");
                    }
                }
                Utility.tipsyfy();
            });
        }
        function promptCreate()
        {
            $("#createRoleId").val("");
            $("#createRoleName").val("");
            $("#createRoleQuota").val("");
            $("#createRoleEmail").val("");
            $("#roleCreateBox").dialog("open");
        }
        function promptUpdate(roleId, roleName, email, quota)
        {
            $("#updateRoleId").val(roleId);
            $("#updateRoleName").val(roleName);
            $("#updateRoleEmail").val(email);
            $("#updateRoleQuota").val(quota);
            $("#roleUpdateBox").dialog("open");
        }
        function rowClick(roleId)
        {
            $(".menuRoles").each(function(index) { $(this).addClass("hidden");}); // Hide other menus
            if($("#role_"+roleId).hasClass("rowSelected"))
            {
                $(".roleRow").each(function(index) { $(this).removeClass("rowSelected");}); // Deselects other rows
                $("#role_"+roleId).removeClass("rowSelected"); // Select the row of the file
                $("#roleNameElement_"+roleId).removeClass("leftborder");
                $("#menu_row_"+roleId).addClass("hidden"); // Show the menu on the selected file
            }
            else
            {
                $(".roleRow").each(function(index) { $(this).removeClass("rowSelected");}); // Deselects other rows
                $("#role_"+roleId).addClass("rowSelected"); // Select the row of the file
                $("#roleNameElement_"+roleId).addClass("leftborder");
                $("#menu_row_"+roleId).removeClass("hidden"); // Show the menu on the selected file
            }
        }
        function selectAll()
        {
            $(".roleSelectBox").prop("checked", $("#allRolesCheckbox").prop("checked"));
        }

        RoleMember = function() {
            function add(userIds, roleId)
            {
                var action = "adding user to role";
                if(userIds !== "" && roleId !== "")
                {
                    var data = {
                        userIds: userIds,
                        roleId: roleId
                    };
                    Filelocker.request("/account/add_users_to_role", action, data, true, function() {
                        Admin.Role.prompt(roleId);
                    });
                }
                else
                    StatusResponse.create("adding user to role", "Select user and role.", false);
            }
            function remove(userIds, roleId, context)
            {
                var data = {
                    userIds: userIds,
                    roleId: roleId
                };
                Filelocker.request("/account/remove_users_from_role", "removing users from role", data, true, function() {
                    if(context === "rollout")
                        Admin.Role.load();
                    else if(context === "viewRoleBox")
                        Admin.Role.prompt(roleId);
                });
            }
            return {
                add:add,
                remove:remove
            };
        }();

        return {
            load:load,
            create:create,
            update:update,
            del:del,
            prompt:prompt,
            promptCreate:promptCreate,
            promptUpdate:promptUpdate,
            rowClick:rowClick,
            selectAll:selectAll,
            Member:RoleMember
        };
    }();
    
    Attribute = function() {
        function create()
        {
            var data = {
                attributeId: $("#createAttributeId").val(),
                attributeName: $("#createAttributeName").val()
            };
            Filelocker.request("/account/create_attribute", "creating attribute", data, true, function() {
                $("#attributeCreateBox").dialog("close");
                load(Defaults.adminAttributesTabIndex);
            });
        }
        function del()
        {
            var action = "deleting attribute";
            var attributeIds = "";
            $("#attributeTable :checked").each(function() { attributeIds += $(this).val()+","; });
            if(attributeIds !== "")
            {
                Filelocker.request("/account/delete_attributes", action, {attributeIds: attributeIds}, true, function() {
                    load(Defaults.adminAttributesTabIndex);
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
            var action = "loading permissions";
            Filelocker.request("/account/get_user_permissions", action, {userId: userId}, false, function(returnData) {
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
                    $("#permissionsTable").append("<tr id='permission_"+permRow.permissionId+"' class='fileRow'><td><input type='checkbox' value='"+permRow.permissionId+"' id='checkbox_"+i+"' name='select_permission' class='permissionSelectBox' onChange=\"Admin.Permission.changed('"+userId+"','"+permRow.permissionId+"', "+i+")\""+checkedStatus+" "+disabled+"/>"+permRow.permissionId+"</td><td>"+permRow.permissionName+"</td><td>"+permRow.inheritedFrom+"</td></tr>");
                }
                if ($("#permissionsTable tr").length !== 0)
                {
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
                }
                else
                    StatusResponse.create(action, "No permissions were found.", false);
            });
        }
        function grant(data)
        {
            Filelocker.request("/account/grant_user_permission", "granting permission", data, true, function() {
                load(data.userId);
            });
        }
        function revoke(data)
        {
            Filelocker.request("/account/revoke_user_permission", "revoking permission", data, true, function() {
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

    RolePermission = function() {
        function load(roleId)
        {
            var action = "loading permissions";
            Filelocker.request("/account/get_role_permissions", action, {roleId: roleId}, false, function(returnData) {
                $("#rolePermissionsTable").empty();
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
                    $("#rolePermissionsTable").append("<tr id='rolePermission_"+permRow.permissionId+"' class='fileRow'><td><input type='checkbox' value='"+permRow.permissionId+"' id='checkbox_"+i+"' name='select_permission' class='permissionSelectBox' onChange=\"Admin.RolePermission.changed('"+roleId+"','"+permRow.permissionId+"', "+i+")\""+checkedStatus+" "+disabled+"/>"+permRow.permissionId+"</td><td>"+permRow.permissionName+"</td><td>"+permRow.inheritedFrom+"</td></tr>");
                }
                if ($("#rolePermissionsTable tr").length !== 0)
                {
                    $("#rolePermissionTableSorter").tablesorter({
                        headers: {
                            0: {sorter: 'text'},
                            1: {sorter: 'text'},
                            2: {sorter: 'text'}
                        }
                    });
                    $("#rolePermissionTableSorter").trigger("update");
                    $("#rolePermissionTableSorter").trigger("sorton",[[[0,0]]]);
                    $("#roleUpdatePermissionsBox").dialog("open");
                }
                else
                    StatusResponse.create(action, "No permissions were found.", false);
            });
        }
        function grant(data)
        {
            Filelocker.request("/account/grant_role_permission", "granting permission", data, true, function() {
                load(data.roleId);
            });
        }
        function revoke(data)
        {
            Filelocker.request("/account/revoke_role_permission", "revoking permission", data, true, function() {
                load(data.roleId);
            });
        }
        function changed(roleId, permissionId, rowId)
        {
            var data = {
                roleId: roleId,
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
                Filelocker.request("/admin/get_template_text", "loading template", {templateName:$('#template_selector').val()}, false, function(returnData) {
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

    Statistics = function() {
        function show()
        {
            getHourlyStatistics();
            getDailyStatistics();
            getMonthlyStatistics();
            $("#systemStatistics").tabs();
            setTimeout(function(){ $("#systemStatisticsBox").dialog("open"); }, 300);
        }
        function getHourlyStatistics()
        {
            $("#hourly").empty();
            $.post(FILELOCKER_ROOT+'/file/get_hourly_statistics?format=json&ms=' + new Date().getTime(), {},
            function(returnData) {
                var hourlyTable = "<div class='statisticsTableWrapper'><table id='hourlyStatisticsTable' class='statisticsTable'><colgroup><col class='colHead' /></colgroup><caption>% of Total Usage by Hour (Last 30 Days)</caption><thead><tr><td class='rowHead'>Hour</td>";
                var hourlyHeaders = "";
                var hourlyDownloadData = "";
                var hourlyUploadData = "";
                for (var i=0; i<24; i++)
                {
                    hourlyHeaders += "<th scope='col'>"+i+"</th>";
                    var hasDownloadData = false;
                    var hasUploadData = false;
                    $.each(returnData.data.downloads, function(key, value) {
                        if (key == i)
                        {
                            hourlyDownloadData += "<td scope='row'>"+value+"</td>";
                            hasDownloadData = true;
                            return false;
                        }
                    });
                    $.each(returnData.data.uploads, function(key, value) {
                        if (key == i)
                        {
                            hourlyUploadData += "<td scope='row'>"+value+"</td>";
                            hasUploadData = true;
                            return false;
                        }
                    });
                    if (!hasDownloadData)
                        hourlyDownloadData += "<td scope='row'>0</td>";
                    if (!hasUploadData)
                        hourlyUploadData += "<td scope='row'>0</td>";
                }
                hourlyTable += hourlyHeaders + "</tr></thead><tbody><tr><th scope='row' class='rowHead'>Downloads</th>" + hourlyDownloadData + "</tr>";
                hourlyTable += "<tr><th scope='row' class='rowHead'>Uploads</th>" + hourlyUploadData + "</tr>";
                hourlyTable += "</tbody></table></div>";
                $("#hourly").html("<div>" + hourlyTable + "</div><br />");
                if(!!document.createElement('canvas').getContext)
                {
                    $("#hourlyStatisticsTable").visualize({
                        type: 'line',
                        width: 600,
                        height: 200,
                        appendKey: true,
                        colors: ['#fee932','#000000'],
                        diagonalLabels: false,
                        labelWidth: 10,
                        yLabelUnit: "%"
                    }).appendTo("#hourly").trigger("visualizeRefresh");
                }
                else
                    $("#hourly").append("<i>Your browser does not support the canvas element of HTML5.</i>");
            }, 'json');
        }
        function getDailyStatistics()
        {
            $("#daily").empty();
            $.post(FILELOCKER_ROOT+'/file/get_daily_statistics?format=json&ms=' + new Date().getTime(), {},
            function(returnData) {
                var dailyTable = "<div class='statisticsTableWrapper'><table id='dailyStatisticsTable' class='statisticsTable'><colgroup><col class='colHead' /></colgroup><caption>Total Usage by Day (Last 30 Days)</caption><thead><tr><td class='rowHead'>Hour</td>";
                var dailyHeaders = "";
                var dailyDownloadData = "";
                var dailyUploadData = "";
                var d = new Date();
                d.setDate(d.getDate()-30);
                for (var i=0; i<=30; i++)
                {
                    var dateToUse = d.getMonth()+1+"/"+d.getDate();
                    dailyHeaders += "<th scope='col'>"+dateToUse+"</th>";
                    var hasDownloadData = false;
                    var hasUploadData = false;
                    $.each(returnData.data.downloads, function(key, value) {
                        if (key == dateToUse)
                        {
                            dailyDownloadData += "<td scope='row'>"+value+"</td>";
                            hasDownloadData = true;
                            return false;
                        }
                    });
                    $.each(returnData.data.uploads, function(key, value) {
                        if (key == dateToUse)
                        {
                            dailyUploadData += "<td scope='row'>"+value+"</td>";
                            hasUploadData = true;
                            return false;
                        }
                    });
                    if (!hasDownloadData)
                        dailyDownloadData += "<td scope='row'>0</td>";
                    if (!hasUploadData)
                        dailyUploadData += "<td scope='row'>0</td>";
                    d.setDate(d.getDate()+1);
                }
                dailyTable += dailyHeaders + "</tr></thead><tbody><tr><th scope='row' class='rowHead'>Downloads</th>" + dailyDownloadData + "</tr>";
                dailyTable += "<tr><th scope='row' class='rowHead'>Uploads</th>" + dailyUploadData + "</tr>";
                dailyTable += "</tbody></table></div>";
                $("#daily").html("<div>" + dailyTable + "</div><br />");
                if(!!document.createElement('canvas').getContext)
                {
                    $("#dailyStatisticsTable").visualize({
                        type: 'line',
                        width: 600,
                        height: 200,
                        appendKey: true,
                        colors: ['#fee932','#000000'],
                        diagonalLabels: true,
                        dottedLast: true,
                        labelWidth: 10
                    }).appendTo("#daily").trigger("visualizeRefresh");
                }
                else
                    $("#daily").append("<i>Your browser does not support the canvas element of HTML5.</i>");
            }, 'json');
        }
        function getMonthlyStatistics()
        {
            $("#monthly").empty();
            $.post(FILELOCKER_ROOT+'/file/get_monthly_statistics?format=json&ms=' + new Date().getTime(), {},
            function(returnData) {
                var monthlyTable = "<div class='statisticsTableWrapper'><table id='monthlyStatisticsTable' class='statisticsTable'><colgroup><col class='colHead' /></colgroup><caption>Total Usage by Month (Last 12 Months)</caption><thead><tr><td class='rowHead'>Month</td>";
                var monthlyHeaders = "";
                var monthlyDownloadData = "";
                var monthlyUploadData = "";
                var months = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}
                var now = new Date().getMonth()+1;
                for (var i=1; i<=12; i++)
                {
                    var month = 0;
                    if (now+i > 12)
                        month = now+i-12;
                    else
                        month = now+i;
                    monthlyHeaders += "<th scope='col'>"+months[month]+"</th>";
                    var hasDownloadData = false;
                    var hasUploadData = false;
                    $.each(returnData.data.downloads, function(key, value) {
                        if (key == month)
                        {
                            monthlyDownloadData += "<td scope='row'>"+value+"</td>";
                            hasDownloadData = true;
                            return false;
                        }
                    });
                    $.each(returnData.data.uploads, function(key, value) {
                        if (key == month)
                        {
                            monthlyUploadData += "<td scope='row'>"+value+"</td>";
                            hasUploadData = true;
                            return false;
                        }
                    });
                    if (!hasDownloadData)
                        monthlyDownloadData += "<td scope='row'>0</td>";
                    if (!hasUploadData)
                        monthlyUploadData += "<td scope='row'>0</td>";
                }
                monthlyTable += monthlyHeaders + "</tr></thead><tbody><tr><th scope='row' class='rowHead'>Downloads</th>" + monthlyDownloadData + "</tr>";
                monthlyTable += "<tr><th scope='row' class='rowHead'>Uploads</th>" + monthlyUploadData + "</tr>";
                monthlyTable += "</tbody></table></div>";
                $("#monthly").html("<div>" + monthlyTable + "</div><br />");
                if(!!document.createElement('canvas').getContext)
                {
                    $("#monthlyStatisticsTable").visualize({
                        type: 'line',
                        width: 600,
                        height: 200,
                        appendKey: true,
                        colors: ['#fee932','#000000'],
                        diagonalLabels: false,
                        dottedLast: true,
                        labelWidth: 10
                    }).appendTo("#monthly").trigger("visualizeRefresh");
                }
                else
                    $("#monthly").append("<i>Your browser does not support the canvas element of HTML5.</i>");
            }, 'json');
        }
    }();
    
    return {
        load:load,
        getVaultUsage:getVaultUsage,
        updateConfig:updateConfig,
        User:User,
        Role:Role,
        Attribute:Attribute,
        Permission:Permission,
        RolePermission:RolePermission,
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
            Admin.load(Defaults.adminUsersTabIndex);
        }
    });
});