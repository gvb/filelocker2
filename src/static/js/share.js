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
        var publicShareRowTemplate =
        '<tr class="fileRow">\
            <td class="spacer"></td>\
            <td class="publicShareLink"></td>\
            <td class="publicShareType"></td>\
            <td class="publicShareExpires"></td>\
            <td class="publicShareMessage"></td>\
            <td class="publicShareFileCount"></td>\
            <td class="publicShareActions"></td>\
        </tr>';

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
                        message: $("#publicShareMessage").val(),
                        password: $("#publicSharePassword").val(),
                        confirmPassword: $("#publicSharePassword").val(),
                        expiration: $("#publicShareExpiration").val(),
                        shareType: shareType
                    };
                    Filelocker.request("/share/create_public_share", action, data, true, function() {
                        $("#shareMultiBox").dialog("close");
                        prompt();
                    });
                }
            }
        }
        function del(shareId)
        {
            Filelocker.request("/share/delete_public_share", "deleting public share", { shareId:shareId }, true, function() {
                prompt();
            });
        }
        function delByFileID(fileIds)
        {
            Filelocker.request("/share/delete_public_shares_by_file_ids", "deleting all public shares for file(s)", { fileIds:fileIds }, true, function() {
                FLFile.load();
            });
        }
        function prompt(fileIds)
        {
            fileIds = fileIds || $("#filesTable tr.rowSelected input.fileSelectBox").val();

            Filelocker.request("/share/get_public_shares_by_file_ids", "retrieving all public shares for file(s)", { fileIds:fileIds }, false, function(returnData) {
                $("tbody#publicSharesTable").empty();
                $.each(returnData.data, function(index, share){
                    var $row = $(publicShareRowTemplate);
                    var fileList = "";
                    var fileCounter = 0;
                    $row.find("td.publicShareLink").html("<a href='' class='globe'>Link</a>");
                    $row.find("td.publicShareType").text(share.reuse.capitalize());
                    $row.find("td.publicShareExpires").text(share.date_expires);
                    $row.find("td.publicShareMessage").text(share.message);

                    $.each(share.files, function(fileId, fileName) {
                        fileList += fileName + "<br />";
                        fileCounter++;
                    });
                    $row.find("td.publicShareFileCount").html("<span class='publicShareFileList pseudoLink' title='"+fileList+"'>"+fileCounter+" files</span>");
                    $row.find("td.publicShareActions").html("<a href='#' onclick='javascript:Share.Public.del(\""+share.id+"\")' class='inlineLink' title='Delete this public share'><span class='cross'>&nbsp;</span></a>");
                    $("tbody#publicSharesTable").append($row);
                });
                Utility.tipsyfy();
                $("#publicSharesTableSorter").tablesorter({
                    headers: {
                        0: {sorter: false},
                        1: {sorter: false},
                        2: {sorter: 'text'},
                        3: {sorter: 'shortDate'},
                        4: {sorter: 'text'},
                        5: {sorter: 'text'},
                        6: {sorter: false}
                    }
                });
                $("#publicShareManageBox").dialog("open");
            });
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
            delByFileID:delByFileID,
            prompt:prompt,
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