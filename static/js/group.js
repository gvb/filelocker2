Group = function() {
    function load()
    {
        $("#wrapper_2col").load(FILELOCKER_ROOT+"/manage_groups?format=text&ms=" + new Date().getTime(), function (responseText, textStatus, xhr) {
            if (textStatus == "error")
                StatusResponse.create("loading groups", "Error "+xhr.status+": "+xhr.textStatus, false);
            else 
            {
                if ($("#sessionState").length >0 && $("#sessionState").val() == "expired")
                    Filelocker.login();
                else
                {
                    $("#viewGroupBox").dialog($.extend({
                        title: "<span class='view'>View Group Membership</span>",
                        close: function() { load(); }
                    }, Defaults.largeDialog));
                    if($("#groupsTable tr").length>0)
                    {
                        $("#groupTableSorter").tablesorter({
                            headers: {
                                0: {sorter: false},
                                1: {sorter: 'text'},
                                2: {sorter: false},
                                3: {sorter: false}
                            },
                            sortList: [[1,0]]
                        });
                    }
                }
            }
            Utility.getRandomTip();
            Utility.tipsyfy();
        });
    }
    function create()
    {
        if($("#name_new").val().trim() !== "")
        {
            Filelocker.request("/account/create_group", "creating group", { groupName: $("#name_new").val() }, true, function() {
                load();
            });
        }
        else
            StatusResponse.create("creating group", "Group must have a name.", false);
    }
    function update(groupId)
    {
        if($("#name_new").val().trim() !== "")
        {
            var data = {
                groupName: $("#name_new").val(),
                users: "",
                groupId: groupId,
                groupScope: "private"
            };
            Filelocker.request("/account/update_group", "updating group", data, true, function() {
                load();
            });
        }
        else
            StatusResponse.create("renaming group", "Group must have a name.", false);
    }
    function del()
    {
        var groupIds = "";
        $("#groupsTable :checked").each(function() {groupIds+=$(this).val()+",";});
        if(groupIds !== "")
        {
            Filelocker.request("/account/delete_groups", "deleting groups", {groupIds: groupIds}, true, function() {
                load();
            });
        }
        else
            StatusResponse.create("deleting groups", "Select group(s) for deletion.", false);
    }
    function prompt(groupId)
    {
        $("#viewGroupBox").load(FILELOCKER_ROOT+"/account/get_group_members?format=searchbox_html&ms=" + new Date().getTime(), {groupId: groupId}, function (responseText, textStatus, xhr) {
            if (textStatus == "error")
                StatusResponse.create("loading group membership", "Error "+xhr.status+": "+xhr.textStatus, false);
            else {
                if ($("#sessionState").length >0 && $("#sessionState").val() == "expired")
                    Filelocker.login();
                else
                {
                    $("#viewGroupBox").dialog($.extend({
                        title: "<span class='view'>View Group Membership</span>"
                    }, Defaults.largeDialog));
                    $("#current_members").accordion({ autoHeight: false });
                    Account.Search.init("manage_groups");
                    $("#viewGroupBox").dialog("open");
                }
            }
            Utility.tipsyfy();
        });
    }
    function promptAdd()
    {
        if($("#group_new").length > 0)
            StatusResponse.create("adding new group", "You are currently in the process of adding/editing a group.", false);
        else
        {
            $("#groupsTable").append("<tr id='group_new' class='groupRow'><td id='groupNameElement_new' class='groupNameElement'><input id='checkbox_new' type='checkbox' disabled='disabled'></td><td><input id='name_new' type='text'></input>&nbsp;<a href='javascript:Group.create();' class='inlineLink' title='Create Group'><span class='plus'>&nbsp;</span></a><a href='javascript:Group.load();' class='inlineLink' title='Cancel Group Creation'><span class='cross'>&nbsp;</span></a></td><td>Not editable</td><td class='dropdownArrow rightborder'></td></tr>");
            if($.browser.mozilla)
                $("#name_new").keypress(addGroupIfEnter); 
            else
                $("#name_new").keydown(addGroupIfEnter);
            $("#name_new").focus();
        }
    }
    function promptEdit(groupId, currentName)
    {
        if($("#group_new").length > 0)
            StatusResponse.create("editing group", "You are currently in the process of adding/editing a group.", false);
        else
        {
            var numRows = $("#groupsTable tr").length;
            var rowModifier = "";
            if((numRows+1) % 2 == 1)
                rowModifier = "oddRow";
            $("#group_" + groupId).empty();
            var rowhtml = "<td id='groupNameElement_new' class='groupNameElement'>";
            rowhtml += "<input id='checkbox_new' type='checkbox' disabled='disabled'/></td><td><input id='name_new' type='text' value='"+currentName+"'></input>&nbsp;&nbsp;";
            rowhtml += "<a href='javascript:Group.update("+groupId+");' class='inlineLink' title='Save New Name'><span class='save'>&nbsp;</span></a>";
            rowhtml += "<a href='javascript:Group.load();' class='inlineLink' title='Cancel Rename'><span class='cross'>&nbsp;</span></a></td>";
            rowhtml += "<td>Renaming...</td><td class='dropdownArrow rightborder'></td><input type='hidden' id='group_new' />";
            $("#group_" + groupId).append(rowhtml);
            $("#name_new").focus();
            $("#name_new").select();
            if($.browser.mozilla)
                $("#name_new").keypress(function(event) { editGroupIfEnter(event, groupId); }); 
            else
                $("#name_new").keydown(function(event) { editGroupIfEnter(event, groupId); });
        }
    }
    
    function addGroupIfEnter(event) { if (event.keyCode == 13) create(); }
    function editGroupIfEnter(event, groupId) { if (event.keyCode == 13) update(groupId); }
    function rowClick(groupId)
    {
        $(".menuGroups").each(function() { $(this).addClass("hidden");}); // Hide other menus
        if($("#group_"+groupId).hasClass("rowSelected"))
        {
            $(".groupRow").each(function() { $(this).removeClass("rowSelected");}); // Deselects other rows
            $("#group_"+groupId).removeClass("rowSelected"); // Select the row of the file
            $("#groupNameElement_"+groupId).removeClass("leftborder");
            $("#menu_group_"+groupId).addClass("hidden"); // Show the menu on the selected file
        }
        else
        {
            $(".groupRow").each(function() { $(this).removeClass("rowSelected");}); // Deselects other rows
            $("#group_"+groupId).addClass("rowSelected"); // Select the row of the file
            $("#groupNameElement_"+groupId).addClass("leftborder");
            $("#groupNameElement_new").addClass("leftborder");
            $("#menu_group_"+groupId).removeClass("hidden"); // Show the menu on the selected file
        }
    }
    
    Member = function() {
        function add(userId, groupId)
        {
            if(userId !== "" && groupId !== "")
            {
                var data = {
                    userId: userId,
                    groupId: groupId
                };
                Filelocker.request("/account/add_user_to_group", "adding user to group", data, true, function() {
                    Group.prompt(groupId);
                });
            }
            else
                StatusResponse.create("adding user to group", "Select user and group.", false);
        }
        function remove(userIds, groupId, context)
        {
            var data = {
                userIds: userIds,
                groupId: groupId
            };
            Filelocker.request("/account/remove_users_from_group", "removing users from group", data, true, function() {
                if(context === "rollout")
                    Group.load();
                else if(context === "viewGroupBox")
                    Group.prompt(groupId);
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
        promptAdd:promptAdd,
        promptEdit:promptEdit,
        rowClick:rowClick,
        Member:Member
    };
}();