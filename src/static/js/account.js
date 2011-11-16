Account = function() {
    function update(userId)
    {
        var runUpdate = true;
        var emailRegEx = /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,4}$/i;
        if($("#userPassword").val() != $("#userPasswordConfirm").val())
        {
            StatusResponse.create("updating user account", "Passwords do not match.", false);
            runUpdate = false;
        }
        if($("#userEmail").val() !== "" && $("#userEmail").val().search(emailRegEx) == -1)
        {
            StatusResponse.create("updating user account", "Email address is not valid.", false);
            runUpdate = false;
        }
        if(runUpdate)
        {
            var data = {};
            data.userId = userId;
            if ($("#userPassword").val() !== "")
            {
                data.password = $("#userPassword").val();
                data.confirmPassword =  $("#userConfirmPassword").val();
            }
            data.emailAddress = $("#userEmail").val();
            Filelocker.request("/account/update_user", "updating user account", data, function() {
                $("#editAccountBox").dialog("close");
            });
        }
    }
    function prompt()
    {
        $("#userPassword").val("");
        $("#userPasswordConfirm").val("");
        //getCLIKeyList();
        $("#editAccountBox").dialog("open");
    }
    function toggleRoles()
    {
        $("#availableRoles div").each(function() {
            if($(this).is(':hidden'))
            {
                $(this).show("drop", { direction: "up" }, 200);
                $(".userLoggedInMultiple").addClass("roleBorderNoBottom");
                $(".roleLoggedInMultiple").addClass("roleBorderNoBottom");
                $("#availableRoles").addClass("roleBorderNoTop");
            }
            else
            {
                $(this).hide("drop", { direction: "up" }, 200);
                $(".userLoggedInMultiple").removeClass("roleBorderNoBottom");
                $(".roleLoggedInMultiple").removeClass("roleBorderNoBottom");
                $("#availableRoles").removeClass("roleBorderNoTop");
            }
        });
    }
    function switchRoles(roleUserId)
    {
        var data = {};
        if(roleUserId != null) {
            data = { roleUserId: roleUserId };
            Filelocker.request("/account/switch_roles", "switching roles", data, function() { location.reload(true); });
        }
    }

    Search = function() {
        function init(context)
        {
            $("#"+context+"_externalSearchSelector").hide();
            //Context Must be a valid ID for which to inject the search HTML
            $("#"+context+"_searchTypeChooser").buttonset();
            $("#"+context+"_searchUserId").button({ icons: {primary:'ui-icon-person'} });
            $("#"+context+"_searchName").button({ icons: {primary:'ui-icon-search'} });
            $("#"+context+"_sections").tabs();
            $("#"+context+"_externalSearch").prop("checked", false);
            $("#"+context+"_searchBox").val("").autocomplete({
                source: function(request, response)
                {
                    var data = {format: "autocomplete"};
                    var nameText = "";
                    if ($("#"+context+"_searchName").prop("checked"))
                    {
                        nameText = $("#"+context+"_searchBox").val().replace(/\s+/g, " ").split(" ");
                        if (nameText.length == 1)
                            data.lastName = $("#"+context+"_searchBox").val();
                        else
                        {
                            data.firstName = nameText[0];
                            data.lastName = nameText[1];
                        }
                    }
                    else // Searching by user ID but entered a full name, let's help them out a little...
                    {
                        nameText = $("#"+context+"_searchBox").val().replace(/\s+/g, " ").split(" ");
                        if (nameText.length === 1)
                            data.userId = $("#"+context+"_searchBox").val();
                        else
                        {
                            data.firstName = nameText[0];
                            data.lastName = nameText[1];
                        }
                    }
                    
                    data.external = $("#"+context+"_externalSearch").prop("checked");

                    var callback = function(returnData) {
                        $("#"+context+"_externalSearchSelector").show();
                        if (typeof returnData.data !== undefined && returnData.data.length > 0)
                            response(returnData.data);
                    }
                    Filelocker.request("/account/search_users", "looking up user", data, false, callback);
                },
                minLength: 2,
                focus: function (event, ui)
                {
                    if (ui.item.value !== "0")
                        $("#"+context+"_searchResult").val(ui.item.value);
                    return false;
                },
                select: function(event, ui)
                {
                    select(ui.item.value, ui.item.label, context);
                }
            }).data( "autocomplete" )._renderItem = function( ul, item ) {
                if (item.value === "0")
                    return $("<li class='person_search_result'></li>").data("item.autocomplete", item).append(item.label).appendTo(ul);
                else
                    return $("<li class='person_search_result'></li>").data("item.autocomplete", item).append("<a>"+item.label+"</a>").appendTo(ul);
            };
            Utility.tipsyfy();
        }
        function update(context)
        {
            $("#"+context+"_searchBox").autocomplete("search");
        }
        function select(id, name, context)
        {
            if(id != "0" && context == "private_sharing")
                $("#"+context+"_searchResult").html("<br /><span class='itemTitleMedium'><span class='ownerItem memberTitle' title='"+id+"'>"+name+"</span></span><a href='javascript:Share.User.create(\""+id+"\");' title='Share with "+name+"' class='shareUser'>Share</a><br /><br /><input type='checkbox' id='private_sharing_notifyUser' checked='checked' /><span onclick='javascript:Utility.check(\"private_sharing_notifyUser\");'>Notify via email</span>");
            else if(id != "0" && context == "manage_groups")
                $("#"+context+"_searchResult").html("<br /><span class='itemTitleMedium'><span class='ownerItem memberTitle' title='"+id+"'>"+name+"</span></span><a href='javascript:Group.Member.add(\""+id+"\",\""+$("#manage_groups_selectedGroupId").val()+"\");' title='Add "+name+" to the Group' class='addUser'>Add</a>");
            else if(id != "0" && context == "manage_roles")
                $("#"+context+"_searchResult").html("<br /><span class='itemTitleMedium'><span class='ownerItem memberTitle' title='"+id+"'>"+name+"</span></span><a href='javascript:Admin.Role.Member.add(\""+id+"\",\""+$("#manage_roles_selectedRoleId").val()+"\");' title='Add "+name+" to the role' class='addUser'>Add</a>");
            else if(id != "0" && context == "messages")
                $("#"+context+"_searchResult").html("<br /><span class='itemTitleMedium'><span class='ownerItem memberTitle' title='"+id+"'>"+name+"</span></span><a href='javascript:Message.create(\""+id+"\");' title='Send message to "+name+"' class='shareMessage'>Send</a>");
            $("#"+context+"_searchBox").val("");
            $("#"+context+"_searchResult").show();
            return false;
        }
        function manual(userId, context)
        {
            var data = {
                userId:userId,
                format: "autocomplete"
            };
            var callback = function(returnData) {
                if (returnData.data != null && returnData.data.length > 0)
                {
                    $.each(returnData.data, function(index, result) {
                        select(result.value, result.label, context);
                    });
                }
            }
            Filelocker.request("/account/search_users", "looking up user", data, false, callback);
        }
        function toggleType(context, searchType)
        {
            if (searchType == "userId")
            {
                $("#"+context+"_search_name").prop("checked", false);
                $("#"+context+"_search_userId").prop("checked", true);
                $("#"+context+"_search_name").addClass("hidden");
                $("#"+context+"_search_userId").removeClass("hidden");
            }
            else if (searchType == "name")
            {
                $("#"+context+"_search_userId").prop("checked", false);
                $("#"+context+"_search_name").prop("checked", true);
                $("#"+context+"_search_userId").addClass("hidden");
                $("#"+context+"_search_name").removeClass("hidden");
            }
        }

        return {
            init:init,
            update:update,
            select:select,
            manual:manual,
            toggleType:toggleType
        };
    }();

    

    /*function createCLIKey()
    {
        if($("#CLIKeyHostIP").val().match(/^\b(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b$/))
        {
            var action = "creating CLI key"
            $.post(FILELOCKER_ROOT+'/cli/create_CLIkey?format=json', 
            {
                hostIPv4: $("#CLIKeyHostIP").val(),
                hostIPv6: ""
            }, 
            function(returnData) 
            {
                getCLIKeyList();
            }, 'json');
        }
        else if($("#CLIKeyHostIP").val().match(/^\s*((([0-9A-Fa-f]{1,4}:){7}([0-9A-Fa-f]{1,4}|:))|(([0-9A-Fa-f]{1,4}:){6}(:[0-9A-Fa-f]{1,4}|((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3})|:))|(([0-9A-Fa-f]{1,4}:){5}(((:[0-9A-Fa-f]{1,4}){1,2})|:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3})|:))|(([0-9A-Fa-f]{1,4}:){4}(((:[0-9A-Fa-f]{1,4}){1,3})|((:[0-9A-Fa-f]{1,4})?:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){3}(((:[0-9A-Fa-f]{1,4}){1,4})|((:[0-9A-Fa-f]{1,4}){0,2}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){2}(((:[0-9A-Fa-f]{1,4}){1,5})|((:[0-9A-Fa-f]{1,4}){0,3}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){1}(((:[0-9A-Fa-f]{1,4}){1,6})|((:[0-9A-Fa-f]{1,4}){0,4}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(:(((:[0-9A-Fa-f]{1,4}){1,7})|((:[0-9A-Fa-f]{1,4}){0,5}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:)))(%.+)?\s*$/))
        {
            $.post(FILELOCKER_ROOT+'/cli/create_CLIkey?format=json', 
            {
                hostIPv4: "",
                hostIPv6: $("#CLIKeyHostIP").val().toLowerCase()
            }, 
            function(returnData) 
            {
                getCLIKeyList();
            }, 'json');
        }
        else
            StatusResponse.create("creating CLI key", "Not a valid IPv4 or IPv6 address.", false);
    }
    function regenerateCLIKey(hostIP)
    {
        $("#CLIKeyHostIP").val(hostIP);
        createCLIKey();
    }
    function getCLIKeyList()
    {
        $("#CLIKeyTable").html("");
        $("#CLIKeyHostIP").val(HOST_IP);
        $.post(FILELOCKER_ROOT+'/cli/get_CLIkey_list?format=json', 
        {}, 
        function(returnData) 
        {
            var html = "";
            $.each(returnData.data, function(index, value) {
                var hostIP = (value.hostIPv6 === "") ? value.hostIPv4 : value.hostIPv6;
                html += "<tr id='"+index+"_CLIKey' class='groupRow'><td></td><td>"+hostIP+"</td><td>"+value.value+"</td>";
                html += "<td><a href='javascript:regenerateCLIKey(\""+hostIP+"\");' class='inlineLink' title='Regenerate CLI key for this host'><span class='refresh'>&nbsp;</span></a>";
                html += "<form style='display:inline;' action='"+FILELOCKER_ROOT+"/cli/download_CLIconf' method='POST' id='downloadCLIConf_"+value.value+"'><a href='javascript:$(\"#downloadCLIConf_"+value.value+"\").submit()' class='inlineLink' title='Download CLI configuration file for this host'><span class='save'>&nbsp;</span></a><input type='hidden' name='CLIKey' value='"+value.value+"'/></form>";
                html += "<a href='javascript:deleteCLIKey(\""+hostIP+"\");' class='inlineLink' title='Delete CLI key for this host'><span class='cross'>&nbsp;</span></a></td>";
                html += "</tr>";
            });
            if(html === "")
                html = "<tr><td></td><td><i>You have not generated any CLI keys.</i></td><td></td><td></td><td></td></tr>";
            $("#CLIKeyTable").append(html);
            $("#CLIKeyTableSorter").trigger("update");
            $("#CLIKeyTableSorter").trigger("sorton",[[[1,0]]]);
            Utility.tipsyfy();
        }, 'json');
    }
    function deleteCLIKey(hostIP)
    {
        if(hostIP.match(/\b(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b/))
        {
            $.post(FILELOCKER_ROOT+'/cli/delete_CLIkey?format=json', 
            {
                hostIPv4: hostIP,
                hostIPv6: ""
            }, 
            function(returnData) 
            {
                getCLIKeyList();
            }, 'json');
        }
        else if(hostIP.match(/^\s*((([0-9A-Fa-f]{1,4}:){7}([0-9A-Fa-f]{1,4}|:))|(([0-9A-Fa-f]{1,4}:){6}(:[0-9A-Fa-f]{1,4}|((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3})|:))|(([0-9A-Fa-f]{1,4}:){5}(((:[0-9A-Fa-f]{1,4}){1,2})|:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3})|:))|(([0-9A-Fa-f]{1,4}:){4}(((:[0-9A-Fa-f]{1,4}){1,3})|((:[0-9A-Fa-f]{1,4})?:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){3}(((:[0-9A-Fa-f]{1,4}){1,4})|((:[0-9A-Fa-f]{1,4}){0,2}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){2}(((:[0-9A-Fa-f]{1,4}){1,5})|((:[0-9A-Fa-f]{1,4}){0,3}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){1}(((:[0-9A-Fa-f]{1,4}){1,6})|((:[0-9A-Fa-f]{1,4}){0,4}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(:(((:[0-9A-Fa-f]{1,4}){1,7})|((:[0-9A-Fa-f]{1,4}){0,5}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:)))(%.+)?\s*$/))
        {
            $.post(FILELOCKER_ROOT+'/cli/delete_CLIkey?format=json', 
            {
                hostIPv4: "",
                hostIPv6: hostIP
            }, 
            function(returnData) 
            {
                getCLIKeyList();
            }, 'json');
        }
        else if (hostIP == "")
        {
            $.post(FILELOCKER_ROOT+'/cli/delete_CLIkey?format=json', 
            {
                hostIPv4: "",
                hostIPv6: ""
            }, 
            function(returnData) 
            {
                getCLIKeyList();
            }, 'json');
        }
    }*/
    
    return {
        update:update,
        prompt:prompt,
        toggleRoles:toggleRoles,
        switchRoles:switchRoles,
        Search:Search
    };
}();