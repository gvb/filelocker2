Share = function() {
    function prompt(fileId, accordionIndex, tabIndex)
    {
        //todo var fileIds = fileId || $.each...
        var fileIds = "";
        if (fileId != null)
            fileIds = fileId;
        else
        {
            $("#filesTable .fileSelectBox:checked").each(function() {
                fileIds+=$(this).val()+",";
            });
        }

        //todo no .load
        $("#shareMultiBox").load(FILELOCKER_ROOT+"/file/get_user_file_list?format=searchbox_html&ms=" + new Date().getTime(), {fileIdList: fileIds}, function (responseText, textStatus, xhr) {
            if (textStatus == "error")
                StatusResponse.create("loading sharing page", "Error "+xhr.status+": "+xhr.textStatus, false);
            else
            {
                if ($("#sessionState").length >0 && $("#sessionState").val() == "expired")
                    Filelocker.login();
                else
                {
                    $("#shareMultiBox").dialog($.extend({
                        title: "<span class='share'>Share a File</span>"
                    }, Defaults.largeDialog));
                    Account.Search.init("private_sharing");
                    $("#current_shares").accordion({ autoHeight: false });
                    if(accordionIndex != null)
                        $("#current_shares").accordion("activate", tabIndex);
                    if(tabIndex != null)
                        $("#private_sharing_sections").tabs("select", tabIndex);

                    $("#publicShareEmail").val("");
                    $("#publicSharePassword").val("");
                    $("#publicSharePasswordConfirm").val("");
                    $("#publicShareExpiration").datepicker("destroy").datepicker({dateFormat: 'mm/dd/yy', showAnim: 'slideDown', minDate: 0});
                    $("#publicShareExpiration").val(DEFAULT_EXPIRATION);

                    $("#shareMultiBox").dialog("open");
                }
            }
            Utility.tipsyfy();
        });
    }
    function hide(fileId)
    {
        Filelocker.request("/share/hide_shares", "hiding share", {fileIds: fileId}, true, function() {
            FLFile.load();
        });
    }
    function unhide()
    {
        Filelocker.request("/share/unhide_shares", "unhiding shares", {}, true, function() {
            $("#editAccountBox").dialog("close");
            FLFile.load();
        });
    }
    function hideMulti()
    {
        if ($("#multiShare").is(':visible'))
            $("#multiShare").hide();
    }
    function showMulti()
    {
        if ($("#multiShare").is(':hidden'))
            $("#multiShare").show("clip", {}, 500);
    }

    UserShare = function() {
        function create(userId, fileId)
        {
            var action = "sharing files with users";
            var fileIds = fileId || $("#selectedFiles").val();
            if(fileIds === "" || fileIds === ",")
                StatusResponse.create(action, "Select file(s) for sharing.", false);
            else
            {
                var notify = $("#private_sharing_notifyUser").is(":checked") ? "yes" : "no";
                Filelocker.request("/share/create_user_shares", action, {fileIds: fileIds, userId: userId, notify: notify}, true, function() {
                    Share.prompt(fileIds, 0, 0);
                });
            }
        }
        function del(userId, fileId)
        {
            var action = "unsharing files with users";
            var fileIds = "";
            if (fileId != null)
                fileIds = fileId;
            else
            {
                selectedFiles = [];
                $("#sharesTable .fileSelectBox:checked").each(function() {selectedFiles.push($(this).val());});
                $.each(selectedFiles, function(index,value) {
                    fileIds += value + ",";
                });
            }

            if(fileIds === "" || fileIds === ",")
                StatusResponse.create(action, "Select file(s) for unsharing.", false);
            else
            {
                Filelocker.request("/share/delete_user_shares", action, {fileIds: fileIds, userId: userId}, true, function() {
                    Share.prompt(fileIds, 0, 0);
                });
            }
        }
        return {
            create:create,
            del:del
        }
    }();

    GroupShare = function() {
        function create(groupId, fileId)
        {
            var action = "sharing files with groups";
            var fileIds = fileId || $("#selectedFiles").val();
            if(fileIds === "" || fileIds === ",")
                StatusResponse.create(action, "Select file(s) for sharing.", false);
            else
            {
                var notify = $("#private_sharing_notifyGroup").is(":checked") ? "yes" : "no";
                Filelocker.request("/share/create_group_shares", action, {fileIds: fileIds, groupId: groupId, notify: notify}, true, function() {
                    Share.prompt(fileIds, 1, 1);
                });
            }
        }
        function del(groupId, fileId)
        {
            var action = "unsharing files with groups";
            var fileIds = "";
            if (fileId != null)
                fileIds = fileId;
            else
            {
                selectedFiles = [];
                $("#sharesTable .fileSelectBox:checked").each(function() {selectedFiles.push($(this).val());});
                $.each(selectedFiles, function(index,value) {
                    fileIds += value + ",";
                });
            }

            if(fileIds === "" || fileIds === ",")
                StatusResponse.create(action, "Select file(s) for unsharing.", false);
            else
            {
                Filelocker.request("/share/delete_group_shares", action, {fileIds: fileIds, groupId: groupId}, true, function() {
                    Share.prompt(fileIds, 1, 1);
                });
            }
        }
        return {
            create:create,
            del:del
        };
    }();

    AttributeShare = function() {
        function create(attributeId, fileId)
        {
            var action = "sharing files by attribute";
            var fileIds = fileId || $("#selectedFiles").val();
            if(fileIds === "" || fileIds === ",")
                StatusResponse.create(action, "Select file(s) for sharing.", false);
            else
            {
                Filelocker.request("/share/create_attribute_shares", action, {fileIds: fileIds, attributeId: attributeId}, true, function() {
                    Share.prompt(fileIds, 2, 2);
                });
            }
        }
        function del(attributeId, fileId)
        {
            var action = "unsharing files by attribute";
            var fileIds = "";
            if (fileId != null)
                fileIds = fileId;
            else
            {
                selectedFiles = [];
                $("#sharesTable .fileSelectBox:checked").each(function() {selectedFiles.push($(this).val());});
                $.each(selectedFiles, function(index,value) {
                    fileIds += value + ",";
                });
            }

            if(fileIds === "" || fileIds === ",")
                StatusResponse.create(action, "Select file(s) for unsharing.", false);
            else
            {
                Filelocker.request("/share/delete_attribute_shares", action, {fileIds: fileIds, attributeId: attributeId}, true, function() {
                    Share.prompt(fileIds, 2, 2);
                });
            }
        }
        return {
            create:create,
            del:del
        };
    }();

    PublicShare = function() {
        function create()
        {
            var action = "sharing file(s)"
            if ($("#publicShareExpirationDate").val() === "")
                StatusResponse.create(action, "Public shares must have an expiration date.", false);
            else if ($("#publicSharePassword").val() != $("#publicSharePasswordConfirm").val())
                StatusResponse.create(action, "Passwords must match for public share.", false);
            else if ($("#publicSharePassword").val() === "" && $("#publicShareType").is(":checked"))
                StatusResponse.create(action, "You must enter a password when creating a multi-use public share.", false);
            else {
                var fileIds = $("#selectedFiles").val();
                if(fileIds === "" || fileIds === ",")
                    StatusResponse.create(action, "Select file(s) for sharing.", false);
                else
                {
                    var shareType = $("#publicShareType").is(":checked") ? "multi" : "single";
                    var data = {
                        fileIds: fileIds,
                        notifyEmails: $("#publicShareEmail").val(),
                        password: $("#publicSharePassword").val(),
                        expiration: $("#publicShareExpiration").val(),
                        shareType: shareType
                    };
                    Filelocker.request("/share/create_public_share", action, data, true, function() {
                        $("#publicShareBox").dialog("close");
                        promptView();
                    });
                }
            }
        }
        function del(shareId)
        {
            Filelocker.request("/share/delete_public_share", "deleting public share", { shareId:shareId }, true, function() {
                FLFile.load();
            });
        }
        function promptView(shareId)
        {
            var linkText = FILELOCKER_ROOT+"/public_download?shareId="+shareId;
            $("#publicShareURL").html("<p><a href='"+linkText+"' target='_blank'>"+linkText+"</a></p>");
            $("#publicShareLinkBox").dialog("open");
        }

        function togglePassword()
        {
            if ($("#publicSharePasswordSelector").is(":checked"))
                $("#publicShareSelector").show();
            else
            {
                $("#publicShareSelector").hide();
                $("#publicSharePassword").val("");
                $("#publicSharePasswordConfirm").val("");
            }
        }
        function toggleType()
        {
            if ($("#publicShareType").is(":checked") && !$("#publicSharePasswordSelector").is(":checked"))
            {
                Utility.check("publicSharePasswordSelector");
                togglePassword();
            }
        }
        return {
            create:create,
            del:del,
            promptView:promptView,
            togglePassword:togglePassword,
            toggleType:toggleType
        };
    }();

    return {
        prompt:prompt,
        hide:hide,
        unhide:unhide,
        hideMulti:hideMulti,
        showMulti:showMulti,
        User:UserShare,
        Group:GroupShare,
        Attribute:AttributeShare,
        Public:PublicShare
    };
}();