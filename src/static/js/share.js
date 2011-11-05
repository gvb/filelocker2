Share = function() {
    function showMulti()
    {
        if ($("#multiShare").is(':hidden'))
            $("#multiShare").show("clip", {}, 500);
    }
    function hideMulti()
    {
        if (!$("#multiShare").is(':hidden'))
            $("#multiShare").hide();
    }
    function prompt(fileId, accordionIndex, tabIndex)
    {
        var fileIds = "";
        if (fileId != null)
            fileIds = fileId;
        else
        {
            $("#filesTable .fileSelectBox:checked").each(function() {
                fileIds+=$(this).val()+",";
            });
        }
        
        $("#shareMultiBox").load(FILELOCKER_ROOT+"/file/get_user_file_list?format=searchbox_html&ms=" + new Date().getTime(), {fileIdList: fileIds}, function (responseText, textStatus, xhr) {
            if (textStatus == "error")
                StatusResponse.create("loading sharing page", "Error "+xhr.status+": "+xhr.textStatus, false);
            else
            {
                if ($("#sessionState").length >0 && $("#sessionState").val() == "expired")
                    Filelocker.login();
                else
                {
                    $("#shareMultiBox").dialog($.extend({}, largePopup, {
                        title: "<span class='share'>Share a File</span>"
                    }));
                    initSearchWidget("private_sharing");
                    $("#current_shares").accordion({ autoHeight: false });
                    if(accordionIndex !== undefined)
                        $("#current_shares").accordion("activate", tabIndex);
                    if(tabIndex !== undefined)
                        $("#private_sharing_sections").tabs("select", tabIndex);
                    $("#shareMultiBox").dialog("open");
                }
            }
            Utility.tipsyfy();
        });
    }

    Public = function() {
        function create()
        {
            if ($("#publicSharePassword").val() != $("#publicSharePasswordConfirm").val())
                StatusResponse.create("sharing file", "Passwords must match for public share.", false);
            else if ($("#publicSharePassword").val() === "" && $("#publicShareType").is(":checked"))
                StatusResponse.create("sharing file", "You must enter a password when creating a multi-use public share.", false);
            else {
                var shareType = $("#publicShareType").is(":checked") ? "multi" : "single";
                var data = {
                    fileId: $("#publicShareFileId").val(),
                    notifyEmails: $("#publicShareEmail").val(),
                    password: $("#publicSharePassword").val(),
                    expiration: $("#publicShareExpiration").val(),
                    shareType: shareType
                };
                Filelocker.request("/share/create_public_share", "sharing files", data, true, function() {
                    $("#publicShareBox").dialog("close");
                    promptView();
                });
            }
        }
        function del(fileId, destination)
        {
            Filelocker.request("/share/delete_public_share", "deleting public share", { fileId:fileId }, true, function() {
                if(destination == "files")
                    File.load();
            });
        }
        function prompt(fileId, fileName, fileExpiration, destination)
        {
            $("#publicShareFileId").val(fileId);
            $("#publicShareEmail").val("");
            $("#publicSharePassword").val("");
            $("#publicSharePasswordConfirm").val("");
            $("#publicShareExpiration").datepicker("destroy");
            if(fileExpiration !== "Never")
            {
                $("#publicShareExpiration").datepicker({dateFormat: 'mm/dd/yy', showAnim: 'slideDown', minDate: 0, maxDate: fileExpiration});
                $("#publicShareExpiration").val(fileExpiration);
            }
            else
            {
                $("#publicShareExpiration").datepicker({dateFormat: 'mm/dd/yy', showAnim: 'slideDown', minDate: 0});
                $("#publicShareExpiration").val(DEFAULT_EXPIRATION);
            }
            $("#publicShareBox").dialog("open");
            $("#publicShareDestination").attr("value",destination);
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
            prompt:prompt,
            promptView:promptView,
            togglePassword:togglePassword,
            toggleType:toggleType
        };
    }();


    function privateShareFiles(shareType, targetId, fileId)
    {
        var fileIds = "";
        if (fileId === null || fileId === undefined)
            fileIds = $("#selectedFiles").val();
        else
            fileIds = fileId;
        if(fileIds === "" || fileIds === ",")
            generatePseudoResponse("sharing files", "Select file(s) for sharing.", false);
        else
        {
            var shareOptions = {};
            var notify = "no";
            var selectedTab = 0;
            if (shareType == "group")
            {
                if ($("#private_sharing_notifyGroup").is(":checked"))
                    notify = "yes";
                shareOptions = {fileIds: fileIds, groupId: targetId, notify: notify};
                selectedTab = 1;
            }
            else if (shareType == "user")
            {
                if ($("#private_sharing_notifyUser").is(":checked"))
                    notify = "yes";
                shareOptions = {fileIds: fileIds, targetId: targetId, notify: notify};
                selectedTab = 0;
            }
            $.post(FILELOCKER_ROOT+'/share/create_private_share?format=json', shareOptions, 
            function(returnData) 
            {
                showMessages(returnData, "sharing files");
                promptShareFiles(fileIds, selectedTab, selectedTab);
            }, 'json');
        }
    }

    function unPrivateShareFiles(targetId, shareType, fileId)
    {
        var fileIds = "";
        if (fileId === null || fileId === undefined)
        {
            selectedFiles = [];
            $("#sharesTable .fileSelectBox:checked").each(function() {selectedFiles.push($(this).val());});
            $.each(selectedFiles, function(index,value) {
                fileIds += value + ",";
            });
        }
        else
            fileIds = fileId;
        
        if(fileIds === "" || fileIds === ",")
            generatePseudoResponse("sharing files", "Select file(s) for un-sharing.", false);
        else
        {
            var selectedTab = 0;
            switch(shareType)
            {
                case 'private': selectedTab = 0; break;
                case 'private_group': selectedTab = 1; break;
                case 'private_attribute': selectedTab = 2; break;
                default: selectedTab = 0; break;
            }
            $.post(FILELOCKER_ROOT+'/share/delete_share?format=json', {fileIds: fileIds, shareType: shareType, targetId: targetId}, 
            function(returnData) 
            {
                showMessages(returnData, "unsharing files");
                promptShareFiles(fileIds, selectedTab, selectedTab);
            }, 'json');
        }
    }

    function hidePrivateShare(fileId)
    {
        $.post(FILELOCKER_ROOT+'/share/hide_share?format=json', {fileIds: fileId}, 
        function(returnData) 
        {
            showMessages(returnData, "hiding share");
            loadMyFiles();
        }, 'json');
    }

    function unhideAllPrivateShares()
    {
        $.post(FILELOCKER_ROOT+'/share/unhide_all_shares?format=json', {}, 
        function(returnData) 
        {
            showMessages(returnData, "unhiding shares");
            $("#editAccountBox").dialog("close");
            loadMyFiles();
        }, 'json');
    }

    function privateAttributeShareFiles(attributeId, fileId)
    {
        var fileIds = "";
        if (fileId === null || fileId === undefined)
            fileIds = $("#selectedFiles").val();
        else
            fileIds = fileId;
        if(fileIds === "" || fileIds === ",")
            generatePseudoResponse("sharing files", "Select file(s) for sharing.", false);
        else
        {
            $.post(FILELOCKER_ROOT+'/share/create_private_attribute_shares?format=json', {fileIds: fileIds, attributeId: attributeId}, 
            function(returnData) 
            {
                showMessages(returnData, "sharing files");
                promptShareFiles(fileIds, 2, 2);
            }, 'json');
        }
    }
    
    return {
        hideMulti:hideMulti,
        showMulti:showMulti,
        prompt:prompt,
        Public:Public
    }
}();