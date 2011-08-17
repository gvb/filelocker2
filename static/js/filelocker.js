var selectedFiles = [];
var selectedFileRow = "";
var statFile = "";
var messageTabs;
var messagePoller;
var uploader=null;
/***Page Loaders***/
// Files
function initFiles()
{
    
    hideMultiShare();
    $(".fileSelectBox").prop("checked", false);
    $(".systemFileSelectBox").prop("checked", false);
    $(".dateFuture").datepicker({dateFormat: 'mm/dd/yy', showAnim: 'slideDown', minDate: 0});
    $(".dateExpire").datepicker({dateFormat: 'mm/dd/yy', showAnim: 'slideDown', minDate: 0, maxDate: DEFAULT_EXPIRATION});
    $(".datePast").datepicker({dateFormat: 'mm/dd/yy', showAnim: 'slideDown', maxDate: 0});
    $("#fileName").prop("checked", false);
    
    $("#uploadBox").dialog($.extend({}, modalDefaults, {
        title: "<span class='upload'>Upload a File</span>",
        width: popup_small_width
    }));
    $("#uploadRequestBox").dialog($.extend({}, modalDefaults, {
        title: "<span class='document_alert'>Request Upload to Filelocker</span>",
        width: popup_small_width
    }));
    $("#uploadRequestLinkBox").dialog($.extend({}, modalDefaults, {
        title: "<span class='globe'>View Public URL for Upload Request</span>",
        width: popup_small_width
    }));
    $("#publicShareLinkBox").dialog($.extend({}, modalDefaults, {
        title: "<span class='globe'>View Public URL</span>",
        width: popup_small_width
    }));
    $("#publicShareBox").dialog($.extend({}, modalDefaults, {
        title: "<span class='globe'>Share a File Publicly</span>",
        width: popup_small_width,
        close: function(event, ui) { loadMyFiles(); }
    }));
    $("#fileNotesBox").dialog($.extend({}, modalDefaults, {
        title: "<span class='view'>View File Notes</span>",
        width: popup_small_width
    }));
    if(GEOTAGGING)
    {
        $("#fileUploadLocationBox").dialog($.extend({}, modalDefaults, {
            title: "<span class='map'>View File Upload Location</span>",
            width: popup_small_width
        }));
    }
    $("#fileStatisticsBox").dialog($.extend({}, modalDefaults, {
        title: "<span class='statistics'>View File Statistics</span>",
        width: popup_large_width
    }));
    $("#shareMultiBox").dialog($.extend({}, modalDefaults, {
        title: "<span class='share'>Share a File</span>",
        width: popup_large_width,
        close: function(event, ui) { loadMyFiles(); }
    }));
    if($("#filesTable tr").length>0)
    {
        $("#fileTableSorter").tablesorter({
            headers: {
                0: {sorter: false},
                1: {sorter: 'text'},
                2: {sorter: 'fileSize'},
                3: {sorter: 'shortDate'},
                4: {sorter: false}
            },
            sortList: [[1,0]],
            textExtraction: 'complex'
        });
    }
    if($("#systemFilesTable tr").length>0)
    {
        $("#systemFileTableSorter").tablesorter({
            headers: {
                0: {sorter: false},
                1: {sorter: 'text'},
                2: {sorter: 'fileSize'},
                3: {sorter: 'shortDate'},
                4: {sorter: false}
            },
            sortList: [[1,0]],
            textExtraction: 'complex'
        });
    }
    if($("#fileSharesTable tr").length>0)
    {
        $("#fileSharesTableSorter").tablesorter({
            headers: {
                0: {sorter: false},
                1: {sorter: 'text'},
                2: {sorter: 'fileSize'},
                3: {sorter: 'shortDate'},
                4: {sorter: false}
            },
            sortList: [[1,0]]
        });
    }
    else
        $("#fileSharesTable").append("<tr class='oddRow'><td class='spacer'></td><td colspan='4'><i>There are no files shared with you.</i></td></tr>");
    if($("#fileAttributeSharesTable tr").length>0)
    {
        $("#fileAttributeSharesTableSorter").tablesorter({
            headers: {
                0: {sorter: false},
                1: {sorter: 'text'},
                2: {sorter: 'fileSize'},
                3: {sorter: 'shortDate'},
                4: {sorter: false}
            },
            sortList: [[1,0]]
        });
    }
    if($("#uploadRequestsTable tr").length>0)
    {
        $("#uploadRequestsTableSorter").tablesorter({
            headers: {
                0: {sorter: false},
                1: {sorter: false},
                2: {sorter: 'text'},
                3: {sorter: 'text'},
                4: {sorter: 'shortDate'},
                5: {sorter: false}
            },
            sortList: [[4,0]]
        });
    }
    else
        $("#uploadRequestsTable").append("<tr class='oddRow'><td class='spacer'></td><td colspan='5'><i>There are no upload requests available.</i></td></tr>");
    $("#miscFilesSections .head").click(function() {
        if ($(this).hasClass("ui-state-default"))
        {
            $(this).removeClass("ui-state-default").addClass("ui-state-active");
            $(this).removeClass("ui-corner-all").addClass("ui-corner-top");
            $(this).attr("aria-expanded", "true");
        }
        else
        {
            $(this).removeClass("ui-state-active").addClass("ui-state-default");
            $(this).removeClass("ui-corner-top").addClass("ui-corner-all");
            $(this).attr("aria-expanded", "false");
        }
        $(this).next().toggle();
        return false;
    }).next().hide();
    $("#fileStatistics").tabs();
    $("#sharedFilesSection").show();
    updateQuota();
    if(selectedFileRow !== "")
        fileRowClick(selectedFileRow);
     
   
                        
}
function loadMyFiles()
{
    $("#wrapper_2col").load(FILELOCKER_ROOT+"/files?format=text&ms=" + new Date().getTime(), {}, function (responseText, textStatus, xhr) {
        if (textStatus == "error")
            generatePseudoResponse("loading files", "Error "+xhr.status+": "+xhr.textStatus, false);
        else
        {
            if ($("#sessionState").length >0 && $("#sessionState").val() == "expired")
                login();
            else
            {
                initFiles();
                if($("#adminBackLink"))
                    $("#adminBackLink").html("<div id='adminLink' class='settings'><a href='javascript:loadAdminInterface()' title='Launch the admin panel'>Admin</a></div>");
                getRandomTip();
                tipsyfy();
            }
        }
    });
}
function takeFile(fileId)
{
    $("#takeOwnership_"+fileId).removeClass("take_ownership");
    $("#takeOwnership_"+fileId).addClass("taking_ownership");
    $.post(FILELOCKER_ROOT+'/file_interface/take_file?format=json', {fileId: fileId}, 
    function(returnData) 
    {
        showMessages(returnData, "taking ownership");
        loadMyFiles();
    }, 'json');   
}
function setGeoData()
{
    if($("#uploadGeolocation").is(":checked") && GEOTAGGING)
    {
        var geoData = "";
        geo_position_js.getCurrentPosition(
        function(position) {
            geoData = "[geo]" + position.coords.latitude + "," + position.coords.longitude + "[/geo]";
            if($("#uploadFileNotes").val() !== "")
                geoData = "\n" + geoData;
            if($("#uploadFileNotes").val().indexOf("[geo]") == -1)
                $("#uploadFileNotes").val($("#uploadFileNotes").val() + geoData);
        },
        function(error) {
            switch(error.code)
            {
                case 1: // User denies permission.
                    if($("#uploadFileNotes").val().match(/\[geo\]-?\d+\.\d+,-?\d+\.\d+\[\/geo\]/g))
                        $("#uploadFileNotes").val($("#uploadFileNotes").val().replace(/\[geo\]-?\d+\.\d+,-?\d+\.\d+\[\/geo\]/g, ""));
                    $("#uploadGeolocation").prop("checked", false);
                    break;
                case 2: // Unable to determine position.
                    generatePseudoResponse("geotagging file upload", "Unable to determine your current location.", false);
                    break;
                case 3: // Takes more than five seconds.
                    generatePseudoResponse("geotagging file upload", "Request for current location has timed out.", false);
                    break;
                default:
                    break;
            }
        },
        {
            enableHighAccuracy: true,
            maximumAge:30000,
            timeout:5000
        });
    }
    else
    {
        if($("#uploadFileNotes").val().match(/\[geo\]-?\d+\.\d+,-?\d+\.\d+\[\/geo\]/g))
            $("#uploadFileNotes").val($("#uploadFileNotes").val().replace(/\[geo\]-?\d+\.\d+,-?\d+\.\d+\[\/geo\]/g, ""));
    }
}

// Shares
function showMultiShare()
{
    if ($("#multiShare").is(':hidden'))
        $("#multiShare").show("clip", {}, 500);
}
function hideMultiShare()
{
    if (!$("#multiShare").is(':hidden'))
        $("#multiShare").hide();
}
function promptShareFiles(fileId, accordionIndex, tabIndex)
{
    var fileIds = "";
    if (fileId !== null && fileId !== undefined)
        fileIds = fileId;
    else
    {
        $("#filesTable .fileSelectBox:checked").each(function() {
            fileIds+=$(this).val()+",";
        });
    }
    
    $("#shareMultiBox").load(FILELOCKER_ROOT+"/file_interface/get_user_file_list?format=searchbox_html&ms=" + new Date().getTime(), {fileIdList: fileIds}, function (responseText, textStatus, xhr) {
        if (textStatus == "error")
            generatePseudoResponse("loading sharing page", "Error "+xhr.status+": "+xhr.textStatus, false);
        else
        {
            if ($("#sessionState").length >0 && $("#sessionState").val() == "expired")
                login();
            else
            {
                $("#shareMultiBox").dialog($.extend({}, modalDefaults, {
                    title: "<span class='share'>Share a File</span>",
                    width: popup_large_width
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
        tipsyfy();
    });
}

// Groups
function loadManageGroups()
{
    $("#wrapper_2col").load(FILELOCKER_ROOT+"/manage_groups?format=text&ms=" + new Date().getTime(), function (responseText, textStatus, xhr) {
        if (textStatus == "error")
            generatePseudoResponse("loading groups", "Error "+xhr.status+": "+xhr.textStatus, false);
        else 
        {
            if ($("#sessionState").length >0 && $("#sessionState").val() == "expired")
                login();
            else
            {
                $("#viewGroupBox").dialog($.extend({}, modalDefaults, {
                    title: "<span class='view'>View Group Membership</span>", 
                    width: popup_large_width,
                    close: function(event, ui) { loadManageGroups(); }
                }));
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
        getRandomTip();
        tipsyfy();
    });
}

// Search
function initSearchWidget(context)
{
    $("#"+context+"_externalSearchSelector").hide();
    //Context Must be a valid ID for which to inject the search HTML
    $("#"+context+"_searchTypeChooser").buttonset();
    $("#"+context+"_searchUserId").button({ icons: {primary:'ui-icon-person'} });
    $("#"+context+"_searchName").button({ icons: {primary:'ui-icon-search'} });
    $("#"+context+"_sections").tabs();
    $("#"+context+"_externalSearch").prop("checked", false);
    $("#"+context+"_searchBox").autocomplete({
        source: function(request, response)
        {
            var searchOptions = {format: "autocomplete"};
            var nameText = "";
            if ($("#"+context+"_searchName").is(":checked"))
            {
                nameText = $("#"+context+"_searchBox").val().replace(/\s+/g, " ").split(" ");
                if (nameText.length == 1)
                    searchOptions.lastName = $("#"+context+"_searchBox").val();
                else
                {
                    searchOptions.firstName = nameText[0];
                    searchOptions.lastName = nameText[1];
                }
            }
            else // Searching by user ID but entered a full name, let's help them out a little...
            {
                nameText = $("#"+context+"_searchBox").val().replace(/\s+/g, " ").split(" ");
                if (nameText.length == 1)
                    searchOptions.userId = $("#"+context+"_searchBox").val();
                else
                {
                    searchOptions.firstName = nameText[0];
                    searchOptions.lastName = nameText[1];
                }
            }
            
            if ($("#"+context+"_externalSearch").is(":checked"))
                searchOptions.external = true;
            else
                searchOptions.external = false;
            
            $.getJSON(FILELOCKER_ROOT+"/user_interface/search_users", searchOptions, function(returnData, textStatus) 
                {
                    $("#"+context+"_externalSearchSelector").show();
                    if (returnData.fMessages.length>0)
                        showMessages(returnData, "looking up user");
                    else if (typeof returnData.data !== undefined && returnData.data.length > 0)
                    {
                        response(returnData.data);
                    }
                });
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
            selectSearchResult(ui.item.value, ui.item.label, context);
        }
    }).data( "autocomplete" )._renderItem = function( ul, item ) {
        if (item.value === "0")
            return $("<li class='person_search_result'></li>").data("item.autocomplete", item).append(item.label).appendTo(ul);
        else
            return $("<li class='person_search_result'></li>").data("item.autocomplete", item).append("<a>"+item.label+"</a>").appendTo(ul);
    };
    tipsyfy();
}
function updateSearch(context)
{
    $("#"+context+"_searchBox").autocomplete("search");
}
function selectSearchResult(userId, userName, context)
{
    if(userId != "0" && context == "private_sharing")
        $("#"+context+"_searchResult").html("<br /><span class='itemTitleMedium'><span class='ownerItem memberTitle' title='"+userId+"'>"+userName+"</span></span><a href='javascript:privateShareFiles(\"user\", \""+userId+"\");' title='Share with "+userName+"' class='shareUser'>Share</a><br /><br /><input type='checkbox' id='private_sharing_notifyUser' checked='checked' /><span onclick='javascript:check(\"private_sharing_notifyUser\");'>Notify via email</span>");
    else if(userId != "0" && context == "manage_groups")
        $("#"+context+"_searchResult").html("<br /><span class='itemTitleMedium'><span class='ownerItem memberTitle' title='"+userId+"'>"+userName+"</span></span><a href='javascript:addUserToGroup(\""+userId+"\",\""+$("#manage_groups_selectedGroupId").val()+"\");' title='Add "+userName+" to the Group' class='addUser'>Add</a>");
    else if(userId != "0" && context == "messages")
        $("#"+context+"_searchResult").html("<br /><span class='itemTitleMedium'><span class='ownerItem memberTitle' title='"+userId+"'>"+userName+"</span></span><a href='javascript:sendMessage(\""+userId+"\");' title='Send message to "+userName+"' class='shareMessage'>Send</a>");
    $("#"+context+"_searchBox").val("");
    $("#"+context+"_searchResult").show();
    return false;
}
function manualSearch(userId, context)
{
    $.getJSON(FILELOCKER_ROOT+"/user_interface/search_users?format=json", {userId: userId}, 
        function(returnData, textStatus) 
        {
            if (returnData.fMessages.length>0)
                showMessages(returnData, "looking up user");
            else if (typeof returnData.data !== undefined && returnData.data.length > 0)
            {
                $.each(returnData.data, function(index, value) {
                    selectSearchResult(value.userId, value.displayName, context);
                });
            }
        });
}

// History
function initHistory()
{
    $(".datePast").datepicker({dateFormat: 'mm/dd/yy', maxDate: 0});
    if($("#historyTableSorter tr").length>2) // Accounts for header and dotted line row
    {
        $("#historyTableSorter").tablesorter({
            headers: {
                0: {sorter: 'isoDate'},
                1: {sorter: 'text'},
                2: {sorter: false}
            },
            sortList: [[0,0]]
        });
    }
    $("#historyLink").removeClass("loading");
    $("#historyLink").addClass("history");
}
function loadHistory()
{
    $("#historyLink").removeClass("history");
    $("#historyLink").addClass("loading");
    var logAction = $("#logActions").val();
    var startDate = $("#historyStartDate").val();
    var endDate = $("#historyEndDate").val();
    var params = {};
    
    if (startDate !== undefined && startDate !== "")
        params.startDate = startDate;
    if (endDate !== undefined && endDate !== "")
        params.endDate = endDate;
    if(logAction !== undefined && logAction !== "")
        params.logAction = logAction;
//     params.userId = userId;
    
    $("#wrapper_2col").load(FILELOCKER_ROOT+"/history?format=html", params, function (responseText, textStatus, xhr) {
        if (textStatus == "error")
            generatePseudoResponse("loading history page", "Error "+xhr.status+": "+xhr.textStatus, false);
        else 
        {
            if ($("#sessionState").length >0 && $("#sessionState").val() == "expired")
                login();
            else
                initHistory();
        }
        if($("#adminBackLink"))
            $("#adminBackLink").html("<div id='adminLink' class='settings'><a href='javascript:loadAdminInterface()' title='Launch the admin panel'>Admin</a></div>");
        tipsyfy();
    });
}

// Messaging
function replyMessage(subject, recipient)
{
    $("#messagesBox").dialog("close");
    if(subject.match(/^RE:/g))
        $("#flMessageSubject").val(subject);
    else
        $("#flMessageSubject").val("RE: " + subject);
    $("#flMessageBody").val("");
    initSearchWidget("messages");
    $("#createMessageBox").dialog("open");
}
/***Interface Functions***/

// Files
function promptUpload()
{
    $("#uploadBox").dialog("open");
    if (uploader == null)
    {
        uploader = $("#uploader").plupload({
                    // General settings
                    runtimes : 'flash,silverlight,html5,html4',
                    url : FILELOCKER_ROOT+'/file_interface/upload?format=json',
                    unique_names : true,
                    chunk_size: '1mb',
                    // Resize images on clientside if we can
                    resize : {width : 320, height : 240, quality : 90},
                    // Flash settings
                    flash_swf_url : FILELOCKER_ROOT+'/static/plupload.flash.swf',
                    silverlight_xap_url : '/static/plupload/plupload.silverlight.xap',
                    init: {
                        FileUploaded: function(up, file, info) {
                                        loadMyFiles();
                                        }
                    }
            });
    }

}
function fileChecked()
{
    var selectedFilesCounter = 0;
    $("#filesTable .fileSelectBox:checked").each(function() {
        selectedFilesCounter ++;
    });
    if ($("#systemFilesTable").length >0)
    {
        $("#systemFilesTable .systemFileSelectBox:checked").each(function() {
            selectedFilesCounter++;
        });
    }

    if (selectedFilesCounter > 1)
        showMultiShare();
    else
        hideMultiShare();
}
function viewFileNotes(fileNotes)
{
    $("#fileNotes").html(fileNotes);
    $("#fileNotesBox").dialog("open");
}
function viewDownloadStatistics(fileId)
{
    $("#totalGraph").empty();
    statFile = fileId;
    var params = {};
    params.fileId = fileId;
    var startDate = $("#totalGraphStartDate").val();
    var endDate = $("#totalGraphEndDate").val();
    if (startDate !== undefined && startDate !== "")
        params.startDate = startDate;
    else
    {
        var d1 = new Date();
        d1.setDate(d1.getDate()-30);
        var dateString1 = ("0" + (d1.getMonth()+1)).slice(-2) + "/" + ("0" + (d1.getDate())).slice(-2) + "/" + d1.getFullYear();
        $("#totalGraphStartDate").val(dateString1);
    }
    if (endDate !== undefined && endDate !== "")
        params.endDate = endDate;
    else
    {
        var d2 = new Date();
        var dateString2 = ("0" + (d2.getMonth()+1)).slice(-2) + "/" + ("0" + (d2.getDate())).slice(-2) + "/" + d2.getFullYear();
        $("#totalGraphEndDate").val(dateString2);
    }

    $.post(FILELOCKER_ROOT+'/file_interface/get_download_statistics?format=json&ms=' + new Date().getTime(), params, 
    function(returnData) {
        var totalTable = "<div class='fileStatisticsTableWrapper'><table id='"+fileId+"_totalDownloads' class='fileStatisticsTable'><colgroup><col class='colHead' /></colgroup><caption>Total Downloads by Day</caption><thead><tr><td class='rowHead'>Date</td>";
        var totalHeaders = "";
        var totalData = "";
        var hasData = false;
        $.each(returnData.data.total, function(key, value) {
            hasData = true;
            totalHeaders += "<th scope='col'>"+value[0]+"</th>";
            totalData += "<td scope='row'>"+value[1]+"</td>";
        });
        totalTable += totalHeaders + "</tr></thead><tbody><tr><th scope='row'  class='rowHead'>Total</th>" + totalData + "</tr></tbody></table></div>";
        if(hasData)
            $("#totalTable").html(totalTable);
        else
            $("#totalTable").html("<i>There are no downloads in the specified date range.</i>");
        
        var uniqueTable = "<div class='fileStatisticsTableWrapper'><table id='"+fileId+"_uniqueDownloads' class='fileStatisticsTable'><colgroup><col class='colHead' /></colgroup><caption>Unique Downloads by Day</caption><thead><tr><td class='rowHead'>Date</td>";
        var uniqueHeaders = "";
        var uniqueData = "";
        hasData = false;
        $.each(returnData.data.unique, function(key, value) {
            hasData = true;
            uniqueHeaders += "<th scope='col'>"+value[0]+"</th>";
            uniqueData += "<td scope='row'>"+value[1]+"</td>";
        });
        uniqueTable += uniqueHeaders + "</tr></thead><tbody><tr><th scope='row' class='rowHead'>Unique</th>" + uniqueData + "</tr></tbody></table></div>";
        if(hasData)
            $("#uniqueTable").html(uniqueTable);
        else
            $("#uniqueTable").html("<i>There are no downloads in the specified date range.</i>");
        
        if(hasData)
        {
            if(!!document.createElement('canvas').getContext)
            {
                $("#"+fileId+"_totalDownloads").visualize({
                    type: 'line',
                    width: 500,
                    height: 200,
                    appendKey: false,
                    colors: ['#fee932','#000000'],
                    diagonalLabels: true,
                    dottedLast: true,
                    labelWidth: 60
                }).appendTo("#totalGraph").trigger("visualizeRefresh");
            }
            else
                $("#totalGraph").html("<i>Your browser does not support the canvas element of HTML5.</i>");
        }
        else
            $("#totalGraph").html("<i>There are no downloads in the specified date range.</i>");
        $("#fileStatisticsBox").dialog("open");
    }, 'json');
}

// Shares
function promptPublicShareFile(fileId, fileName, fileExpiration, destination)
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
function viewPublicShareURL(shareId)
{
    var linkText = FILELOCKER_ROOT+"/public_download?shareId="+shareId;
    $("#publicShareURL").html("<p><a href='"+linkText+"' target='_blank'>"+linkText+"</a></p>");
    $("#publicShareLinkBox").dialog("open");
}
function publicShareFile()
{
    if ($("#publicSharePassword").val() != $("#publicSharePasswordConfirm").val())
        generatePseudoResponse("sharing file", "Passwords must match for public share.", false);
    else if ($("#publicSharePassword").val() === "" && $("#publicShareType").is(":checked"))
        generatePseudoResponse("sharing file", "You must enter a password when creating a multi-use public share.", false);
    else {
        var shareType = "single";
        if($("#publicShareType").is(":checked"))
            shareType = "multi";
        $.post(FILELOCKER_ROOT+'/share_interface/create_public_share?format=json', 
        {
            "fileId": $("#publicShareFileId").val(),
            "notifyEmails": $("#publicShareEmail").val(),
            "password": $("#publicSharePassword").val(),
            "expiration": $("#publicShareExpiration").val(),
            "shareType": shareType
        }, 
        function(returnData) {
            showMessages(returnData, "sharing files");
            $("#publicShareBox").dialog("close");
            if (returnData.data !== undefined && returnData.data !== "")
                viewPublicShareURL(returnData.data);
        }, 'json');
    }
}
function unPublicShareFile(fileId, destination) 
{
    $.post(FILELOCKER_ROOT+'/share_interface/delete_public_share?format=json', 
    {
        "fileId": fileId
    }, 
    function(returnData) {
        showMessages(returnData, "deleting public share");
        if(destination == "files")
            loadMyFiles();
    }, 'json');
}
function togglePublicSharePassword()
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
function togglePublicShareType()
{
    if ($("#publicShareType").is(":checked") && !$("#publicSharePasswordSelector").is(":checked"))
    {
        check("publicSharePasswordSelector");
        togglePublicSharePassword();
    }
}

// Groups
function addGroupIfEnter(event) { if (event.keyCode == 13) createGroup(); }
function promptAddGroup()
{
    if($("#group_new").length > 0)
        generatePseudoResponse("adding new group", "You are currently in the process of adding/editing a group.", false);
    else
    {
        $("#groupsTable").append("<tr id='group_new' class='groupRow'><td id='groupNameElement_new' class='groupNameElement'><input id='checkbox_new' type='checkbox' disabled='disabled'></td><td><input id='name_new' type='text'></input>&nbsp;<a href='javascript:createGroup();' class='inlineLink' title='Create Group'><span class='plus'>&nbsp;</span></a><a href='javascript:loadManageGroups();' class='inlineLink' title='Cancel Group Creation'><span class='cross'>&nbsp;</span></a></td><td>Not editable</td><td class='dropdownArrow rightborder'></td></tr>");
        if($.browser.mozilla)
            $("#name_new").keypress(addGroupIfEnter); 
        else
            $("#name_new").keydown(addGroupIfEnter);
        $("#name_new").focus();
    }
}
function editGroupIfEnter(event, groupId) { if (event.keyCode == 13) updateGroup(groupId); }
function promptEditGroup(groupId, currentName)
{
    if($("#group_new").length > 0)
        generatePseudoResponse("editing group", "You are currently in the process of adding/editing a group.", false);
    else
    {
        var numRows = $("#groupsTable tr").length;
        var rowModifier = "";
        if((numRows+1) % 2 == 1)
            rowModifier = "oddRow";
        $("#group_" + groupId).empty();
        var rowhtml = "<td id='groupNameElement_new' class='groupNameElement'>";
        rowhtml += "<input id='checkbox_new' type='checkbox' disabled='disabled'/></td><td><input id='name_new' type='text' value='"+currentName+"'></input>&nbsp;&nbsp;";
        rowhtml += "<a href='javascript:updateGroup("+groupId+");' class='inlineLink' title='Save New Name'><span class='save'>&nbsp;</span></a>";
        rowhtml += "<a href='javascript:loadManageGroups();' class='inlineLink' title='Cancel Rename'><span class='cross'>&nbsp;</span></a></td>";
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
function promptViewGroup(groupId)
{
    $("#viewGroupBox").load(FILELOCKER_ROOT+"/group_interface/get_group_members?format=searchbox_html&ms=" + new Date().getTime(), {groupId: groupId}, function (responseText, textStatus, xhr) {
        if (textStatus == "error")
            generatePseudoResponse("loading group membership", "Error "+xhr.status+": "+xhr.textStatus, false);
        else {
            if ($("#sessionState").length >0 && $("#sessionState").val() == "expired")
                login();
            else
            {
                $("#viewGroupBox").dialog($.extend({}, modalDefaults, {
                    title: "<span class='view'>View Group Membership</span>",
                    width: popup_large_width
                }));
                $("#current_members").accordion({ autoHeight: false });
                initSearchWidget("manage_groups");
                $("#viewGroupBox").dialog("open");
            }
        }
        tipsyfy();
    });
}

// Search
function toggleSearchType(context, searchType)
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

// Upload Requests
function promptRequestUpload()
{
    $("#uploadRequestEmail").val("");
    $("#uploadRequestMessage").val("");
    $("#uploadRequestPassword").val("");
    $("#uploadRequestPasswordConfirm").val("");
    $("#uploadRequestNotesInfo").html("");
    $("#uploadRequestBox").dialog("open");
}

function viewUploadRequestLink(requestId)
{
    var linkText = FILELOCKER_ROOT+"/public_upload?ticketId="+requestId;
    $("#uploadRequestURL").html("<p><a href='"+linkText+"' target='_blank'>"+linkText+"</a></p>");
    $("#uploadRequestLinkBox").dialog("open");
}

// Messages
function promptCreateMessage()
{
    $("#messagesBox").dialog("close");
    $("#flMessageSubject").val("");
    $("#flMessageRecipientId").val("");
    $("#flMessageBody").val("");
    initSearchWidget("messages");
    $("#createMessageBox").dialog("open");
}

// Edit Account
function loadEditAccount()
{
    $("#userPassword").val("");
    $("#userPasswordConfirm").val("");
    getCLIKeyList();
    $("#editAccountBox").dialog("open");
}

// Misc. Helpers
function selectAll(destination)
{
    if(destination == "files")
    {
        if ($("#selectAllFiles").is(":checked"))
            $(".fileSelectBox").prop("checked", true);
        else
            $(".fileSelectBox").prop("checked", false);
        fileChecked();
    }
    else if(destination == "systemFiles")
    {
        if ($("#selectAllSystemFiles").is(":checked"))
            $(".systemFileSelectBox").prop("checked", true);
        else
            $(".systemFileSelectBox").prop("checked", false);
        fileChecked();
    }
    else if(destination == "manage_shares")
    {
        if ($("#selectAllShares").is(":checked"))
            $(".fileSelectBox").prop("checked", true);
        else
            $(".fileSelectBox").prop("checked", false);
    }
    else if(destination == "manage_shares_force")
    {
        $("#selectAllShares").prop("checked", true);
        $(".fileSelectBox").prop("checked", true);
    }
    else if(destination == "manage_groups")
    {
        if ($("#selectAllGroups").is(":checked"))
            $(".groupSelectBox").prop("checked", true);
        else
            $(".groupSelectBox").prop("checked", false);
    }
    else if(destination == "messageInbox")
    {
        if ($("#selectAllMessageInbox").is(":checked"))
            $(".messageInboxSelectBox").prop("checked", true);
        else
            $(".messageInboxSelectBox").prop("checked", false);
    }
    else if(destination == "messageSent")
    {
        if ($("#selectAllMessageSent").is(":checked"))
            $(".messageSentSelectBox").prop("checked", true);
        else
            $(".messageSentSelectBox").prop("checked", false);
    }
}
function promptConfirmation(func, params)
{
    $("#confirmBox").html("");
    var paramStr = "";
    $.each(params, function(index, value) {
        paramStr += value;
        if(index != params.length-1)
            paramStr += ", ";
    });
    if(func == "deleteFile")
        $("#confirmBox").html("Are you sure you want to delete this file?");
    else if(func == "deleteMessage")
        $("#confirmBox").html("Are you sure you want to delete this message?");
    else if(func == "deleteUploadRequest")
        $("#confirmBox").html("Are you sure you want to delete this upload request?");
    $("#confirmBox").dialog("open").data("funcData", { "func":func, "params":paramStr }).dialog("open");
}

/***AJAX Functions***/

// Files
function fileRowClick(rowId)
{
    selectedFileRow = rowId;
    if ($("#row_"+rowId).hasClass("rowSelected") === false) // Only go through this if it's not already selected
    {
        $(".menuFiles").each(function(index) { $(this).addClass("hidden");}); // Hide other menus
        if($("#row_"+rowId).hasClass("rowSelected"))
        {
            $(".fileRow").each(function(index) { $(this).removeClass("rowSelected");}); // Deselects other rows
            $("#row_"+rowId).removeClass("rowSelected");
            $("#fileName_row_"+rowId).removeClass("leftborder");
            $("#menu_row_"+rowId).addClass("hidden");
        }
        else
        {
            $(".fileRow").each(function(index) { $(this).removeClass("rowSelected");}); // Deselects other rows
            $("#row_"+rowId).addClass("rowSelected"); //Select the row of the file
            $("#fileName_row_"+rowId).addClass("leftborder");
            $("#menu_row_"+rowId).removeClass("hidden"); //Show the menu on the selected file
        }
    }
    else
    {
        $("#row_"+rowId).removeClass("rowSelected");
        $("#fileNameElement_"+rowId).removeClass("leftborder");
        $("#menu_row_"+rowId).addClass("hidden");
    }
}
function toggleNotifyOnDownload(fileId, notifyAction)
{
    var notify = false;
    if(notifyAction == "yes")
        notify = true;
    $.post(FILELOCKER_ROOT+'/file_interface/update_file?format=json', 
    {
        "fileId": fileId,
        "notifyOnDownload": notify
    }, 
    function(returnData) {
        showMessages(returnData, "updating notification settings");
    }, 'json');
}
function deleteFile(fileId)
{
    $.post(FILELOCKER_ROOT+'/file_interface/delete_files?format=json', 
    {"fileIds": fileId}, 
    function(returnData) {
        showMessages(returnData, "deleting file");
        selectedFileRow = "";
        loadMyFiles();
    }, 'json');
}
function deleteFiles()
{
    var fileIds = "";
    selectedFiles = [];
    $("#filesTable .fileSelectBox:checked").each(function() {selectedFiles.push($(this).val());});
    if ($("#systemFilesTable").length >0)
    {
        $("#systemFilesTable .systemFileSelectBox:checked").each(function() {selectedFiles.push($(this).val());});
    }
    $.each(selectedFiles, function(index,value) {
        fileIds += value + ",";
    });
    if(fileIds !== "")
    {
        $.post(FILELOCKER_ROOT+'/file_interface/delete_files?format=json', 
        {"fileIds": fileIds}, 
        function(returnData) {
            showMessages(returnData, "deleting files");
            loadMyFiles();
        }, 'json');
    }
    else
        generatePseudoResponse("deleting files", "Select file(s) for deletion.", false);
}
function updateQuota()
{
    $.getJSON(FILELOCKER_ROOT+'/file_interface/get_quota_usage?format=json&ms=' + new Date().getTime(), 
    function(returnData)
    {
        if (returnData.fMessages.length !== 0)
            showMessages(returnData, "updating quota usage");
        if (typeof returnData.data !== undefined)
        {
            var percentFull = parseInt(parseFloat(returnData.data.quotaUsedMB) / parseFloat(returnData.data.quotaMB) * 100, 10);
            $("#quotaProgressBar").progressbar("value", percentFull);
            $("#quotaProgressBar").attr("title", returnData.data.quotaUsedMB + " MB used out of " + returnData.data.quotaMB + " MB");
        }
    });
}

// Shares
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
        $.post(FILELOCKER_ROOT+'/share_interface/create_private_share?format=json', shareOptions, 
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
        $.post(FILELOCKER_ROOT+'/share_interface/delete_share?format=json', {fileIds: fileIds, shareType: shareType, targetId: targetId}, 
        function(returnData) 
        {
            showMessages(returnData, "unsharing files");
            promptShareFiles(fileIds, selectedTab, selectedTab);
        }, 'json');
    }
}

function hidePrivateShare(fileId)
{
    $.post(FILELOCKER_ROOT+'/share_interface/hide_share?format=json', {fileIds: fileId}, 
    function(returnData) 
    {
        showMessages(returnData, "hiding share");
        loadMyFiles();
    }, 'json');
}

function unhideAllPrivateShares()
{
    $.post(FILELOCKER_ROOT+'/share_interface/unhide_all_shares?format=json', {}, 
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
        $.post(FILELOCKER_ROOT+'/share_interface/create_private_attribute_shares?format=json', {fileIds: fileIds, attributeId: attributeId}, 
        function(returnData) 
        {
            showMessages(returnData, "sharing files");
            promptShareFiles(fileIds, 2, 2);
        }, 'json');
    }
}

// Groups
function groupRowClick(groupId)
{
    $(".menuGroups").each(function(index) { $(this).addClass("hidden");}); // Hide other menus
    if($("#group_"+groupId).hasClass("rowSelected"))
    {
        $(".groupRow").each(function(index) { $(this).removeClass("rowSelected");}); // Deselects other rows
        $("#group_"+groupId).removeClass("rowSelected"); // Select the row of the file
        $("#groupNameElement_"+groupId).removeClass("leftborder");
        $("#menu_group_"+groupId).addClass("hidden"); // Show the menu on the selected file
    }
    else
    {
        $(".groupRow").each(function(index) { $(this).removeClass("rowSelected");}); // Deselects other rows
        $("#group_"+groupId).addClass("rowSelected"); // Select the row of the file
        $("#groupNameElement_"+groupId).addClass("leftborder");
        $("#groupNameElement_new").addClass("leftborder");
        $("#menu_group_"+groupId).removeClass("hidden"); // Show the menu on the selected file
    }
}
function createGroup()
{
    if($("#name_new").val().trim() !== "")
    {
        $.post(FILELOCKER_ROOT+'/group_interface/create_group?format=json', {groupName: $("#name_new").val()}, 
            function(returnData) 
            {
                showMessages(returnData, "creating group");
                loadManageGroups();
            }, 'json');
    }
    else
        generatePseudoResponse("creating group", "Group must have a name.", false);
}
// function bulkRemoveUsersFromGroup(GroupId)
// {
//     memberIds = "";
//     $("#group_table_"+GroupId+" :checked").each(function() {memberIds+=$(this).val()+",";});
//     if(memberIds=="")
//         generatePseudoResponse("removing members", "Select members to remove from this group.", false);
//     else
//         removeUsersFromGroup(memberIds,GroupId);
// }
function removeUsersFromGroup(userIds, groupId, context)
{
    $.post(FILELOCKER_ROOT+'/group_interface/remove_user_from_group?format=json',  {
        userId: userIds,
        groupId: groupId},
        function(returnData) {
            showMessages(returnData, "removing user from group");
            if(context == "rollout")
                loadManageGroups();
            else if(context == "viewGroupBox")
                promptViewGroup(groupId);
        }, 'json');
}
function addUserToGroup(userId, groupId)
{
    if(userId !== "" && groupId !== "")
    {
        $.post(FILELOCKER_ROOT+'/group_interface/add_user_to_group?format=json',  {
            userId: userId,
            groupId: groupId},
            function(returnData) {
                showMessages(returnData, "adding user to group");
                promptViewGroup(groupId);
            }, 'json');
    }
    else
        generatePseudoResponse("adding user to group", "Select user and group.", false);
}
function updateGroup(groupId)
{
    if($("#name_new").val().trim() !== "")
    {
        $.post(FILELOCKER_ROOT+'/group_interface/update_group?format=json',
        {
            groupName: $("#name_new").val(),
            users: "",
            groupId: groupId,
            groupScope: "private"
        },
        function(returnData) 
        {
            showMessages(returnData, "updating group");
            loadManageGroups();
        }, 'json');
    }
    else
        generatePseudoResponse("renaming group", "Group must have a name.", false);
}
function deleteGroups()
{
    var groupIds = "";
    $("#groupsTable :checked").each(function() {groupIds+=$(this).val()+",";});
    if(groupIds !== "")
    {
        $.post(FILELOCKER_ROOT+'/group_interface/delete_group?format=json', {"groupId": groupIds}, 
        function(returnData) {
            showMessages(returnData, "deleting groups");
            loadManageGroups();
        }, 'json');
    }
    else
        generatePseudoResponse("deleting groups", "Select group(s) for deletion.", false);
}

// Upload Request
function deleteUploadRequest(ticketId)
{
    $.post(FILELOCKER_ROOT+'/file_interface/delete_upload_ticket?format=json', {ticketId: ticketId}, 
    function(returnData) 
    {
        showMessages(returnData, "deleting upload request");
        loadMyFiles();
    }, 'json');
}
function createUploadRequest()
{
    if ($("#uploadRequestPassword").val() != $("#uploadRequestPasswordConfirm").val())
        generatePseudoResponse("creating upload request", "Passwords must match for upload request.", false);
//     else if (isNaN(parseInt($("#uploadRequestMaxSize").val())))
//         generatePseudoResponse("creating upload request", "Max upload size must be a number.", false);
//     else if (parseInt($("#uploadRequestMaxSize").val() > USER_QUOTA))
//         generatePseudoResponse("creating upload request", "Max upload size must be lower than your user quota.", false);
    else if ($("#uploadRequestPassword").val() === "" && $("#uploadRequestShareType").is(":checked"))
        generatePseudoResponse("creating upload request", "You must enter a password when creating a multi-use upload request.", false);
    else
    {
        var requestType = "single";
        if($("#uploadRequestShareType").is(":checked"))
            requestType = "multi";
        $.post(FILELOCKER_ROOT+'/file_interface/generate_upload_ticket?format=json', 
        {
            password: $("#uploadRequestPassword").val(),
//             maxFileSize: $("#uploadRequestMaxSize").val(),
            expiration: $("#uploadRequestExpiration").val(),
            scanFile: $("#uploadRequestScanFile").is(":checked"),
            emailAddresses: $("#uploadRequestEmail").val(),
            personalMessage: $("#uploadRequestMessage").val(),
            requestType: requestType
        }, 
        function(returnData) 
        {
            showMessages(returnData, "creating upload request");
            $("#uploadRequestBox").dialog("close");
            loadMyFiles();
        }, 'json');
    }
}
function toggleUploadRequestPassword()
{
    if ($("#uploadRequestPasswordSelector").is(":checked"))
        $("#uploadRequestSelector").show();
    else
    {
        $("#uploadRequestSelector").hide();
        $("#uploadRequestPassword").val("");
        $("#uploadRequestPasswordConfirm").val("");
    }
}
function toggleUploadRequestShareType()
{
    if ($("#uploadRequestShareType").is(":checked") && !$("#uploadRequestPasswordSelector").is(":checked"))
    {
        check("uploadRequestPasswordSelector");
        toggleUploadRequestPassword();
    }
}

// Messages
function getNewMessageCount()
{
    $.getJSON(FILELOCKER_ROOT+'/message_interface/get_new_message_count?format=json&ms=' + new Date().getTime(), 
    function(returnData)
    {
        var noNewMessages = $("#messagesLink").hasClass("messages");
        if (returnData !== null)
        {
            if(returnData.data !== 0)
            {
                $("#messagesLink").removeClass("messages");
                $("#messagesLink").addClass("messagesNew");
                if (returnData.data !== null && returnData.data !== undefined)
                {
                    if(returnData.data == 1)
                        $("#messagesLink a").attr("title",returnData.data + " new message");
                    else
                        $("#messagesLink a").attr("title",returnData.data + " new messages");
                    if(noNewMessages) // If there were no new messages, and now there is...
                        $("#messagesLink").show("pulsate", {times: 10}, 1000);
                }
            }
            else
            {
                if ( $("#messagesLink").hasClass("messagesNew"))
                {
                    $("#messagesLink").removeClass("messagesNew");
                    $("#messagesLink").stop(true, true).fadeIn();
                    $("#messagesLink").css('text-shadow', 'none');
                    $("#messagesLink").css('opacity', 1); // Once the animation stops it will stop on a random opacity. so the opacity needs to be reset to 1.
                }   
                $("#messagesLink").addClass("messages");
                $("#messagesLink a").attr("title","0 new messages");
            }
        }
        else
            clearInterval(messagePoller); // The server might have shut down or something
    });
}
function sendMessage(recipientIds)
{
    $.post(FILELOCKER_ROOT+'/message_interface/send_message?format=json', 
    {
        subject: $("#flMessageSubject").val(),
        body: $("#flMessageBody").val(),
        expiration: $("#flMessageExpiration").val(),
        recipientIds: recipientIds
    }, 
    function(returnData) 
    {
        showMessages(returnData, "sending message");
        if(returnData.fMessages.length === 0)
        {
            $("#createMessageBox").dialog("close");
            viewMessages();
        }
    }, 'json');
}
function viewMessages()
{
    $("#selectAllMessageInbox").prop("checked", false);
    $("#selectAllMessageSent").prop("checked", false);
    $("#messageInboxTable").html("");
    $("#messageSentTable").html("");
    $("#messagesBox").dialog("open");
    $("#messagesBoxTitle").removeClass("messagesTitle");
    $("#messagesBoxTitle").addClass("loading");
    $("#messagesBoxTitle").html("Loading...");
    $.post(FILELOCKER_ROOT+'/message_interface/get_messages?format=json&ms=' + new Date().getTime(),
    function(returnData) {
        if (returnData.fMessages.length !== 0)
            showMessages(returnData, "retrieving messages");
        else
        {
            var recvhtml = "";
            $.each(returnData.data[0], function(index, value) {
                var unreadMessage = "";
                if(value.viewedDatetime === null)
                    unreadMessage = "unreadMessage";
                var shortenedSubject = value.subject;
                if(shortenedSubject.length > 30)
                    shortenedSubject = shortenedSubject.substring(0,22) + "..." + shortenedSubject.substring(shortenedSubject.length-5,shortenedSubject.length);
                recvhtml += "<tr id='"+value.id+"_inbox' class='groupRow "+unreadMessage+"' onClick='javascript:openMessage(\""+value.id+"\",\"inbox\");'>";
                recvhtml += "<td class='leftborder'><input id='"+value.id+"' type='checkbox' class='messageInboxSelectBox' /><span id='"+value.id+"_subject' class='hidden'>"+value.subject+"</span><span id='"+value.id+"_body' class='hidden'>"+value.body+"</span></td>";
                recvhtml += "<td><a href='javascript:openMessage(\""+value.id+"\",\"inbox\");' class='messageLink'>"+value.ownerId+"</a></td><td><a class='messageLink' href='javascript:openMessage(\""+value.id+"\",\"inbox\");'>"+shortenedSubject+"</a></td><td>"+value.creationDatetime+"</td><td class='rightborder'><a href='javascript:replyMessage(\""+value.subject+"\",\""+value.ownerId+"\");javascript:manualSearch(\""+value.ownerId+"\", \"messages\");' class='inlineLink' title='Reply to this message'><span class='replyMessage'>&nbsp;</span></a><a href='javascript:promptConfirmation(\"deleteMessage\", [\""+value.id+"\"]);' class='inlineLink' title='Delete this message'><span class='cross'>&nbsp;</span></a></td>";
                recvhtml += "</tr>";
            });
            if(recvhtml === "")
            {
                recvhtml = "<tr><td></td><td><i>No messages.</i></td><td></td><td></td><td></td></tr>";
                $("#messageSubject").html("");
                $("#messageBody").html("<a href='javascript:viewHelp(\"help_message\");' class='helpLink'>Learn more about Filelocker Messaging.</a>");
            }
            $("#messageInboxTable").append(recvhtml);
            
            var senthtml = "";
            $.each(returnData.data[1], function(index, value) {
                var shortenedSubject = value.subject;
                if(shortenedSubject.length > 30)
                    shortenedSubject = shortenedSubject.substring(0,22) + "..." + shortenedSubject.substring(shortenedSubject.length-5,shortenedSubject.length);
                senthtml += "<tr id='"+value.id+"_sent' class='groupRow ' onClick='javascript:openMessage(\""+value.id+"\",\"sent\");'>";
                senthtml += "<td class='leftborder'><input id='"+value.id+"' type='checkbox' class='messageSentSelectBox' /><span id='"+value.id+"_subject' class='hidden'>"+value.subject+"</span><span id='"+value.id+"_body' class='hidden'>"+value.body+"</span></td>";
                senthtml += "<td><a href='javascript:openMessage(\""+value.id+"\",\"sent\");' class='messageLink'>"+value.messageRecipients+"</a></td><td><a href='javascript:openMessage(\""+value.id+"\",\"sent\");' class='messageLink'>"+shortenedSubject+"</a></td><td>"+value.creationDatetime+"</td><td class='rightborder'><a href='javascript:promptConfirmation(\"deleteMessage\", [\""+value.id+"\"]);' class='inlineLink' title='Delete this message'><span class='cross'>&nbsp;</span></a></td>";
                senthtml += "</tr>";
            });
            if(senthtml === "")
            {
                senthtml = "<tr><td></td><td><i>No messages.</i></td><td></td><td></td><td></td></tr>";
                $("#messageSubject").html("");
                $("#messageBody").html("<a href='javascript:viewHelp(\"help_message\");' class='helpLink'>Learn more about Filelocker Messaging.</a>");
            }
            $("#messageSentTable").append(senthtml);
            
            $("#messageInboxTableSorter").trigger("update");
            $("#messageInboxTableSorter").trigger("sorton",[[[3,1],[2,0]]]);
            $("#messageSentTableSorter").trigger("update");
            $("#messageSentTableSorter").trigger("sorton",[[[3,1],[2,0]]]);
            
            $("#messagesBoxTitle").removeClass("loading");
            $("#messagesBoxTitle").addClass("messagesTitle");
            $("#messagesBoxTitle").html("Messages");
            tipsyfy();
        }
    }, 'json');
}
function openMessage(messageId, context)
{
    $.each($("#messageInboxTable tr"), function(index, value) {
        $(this).removeClass("rowSelected leftborder");
    });
    $.each($("#messageSentTable tr"), function(index, value) {
        $(this).removeClass("rowSelected leftborder");
    });
    if(context == "inbox")
    {
        $("#"+messageId+"_inbox").addClass("rowSelected leftborder rightborder");
        $("#"+messageId+"_inbox").removeClass("unreadMessage");
    }
    else
    {
        $("#"+messageId+"_sent").addClass("rowSelected leftborder rightborder");
    }
    $("#messageSubject").html("<span class='messageHeader'>Subject:</span>" + $("#"+messageId+"_subject").text());
    $("#messageBody").html("<hr class='messageViewBreak' /><span class='messageHeader'>Body:</span>" + $("#"+messageId+"_body").text());
    $.post(FILELOCKER_ROOT+'/message_interface/read_message?format=json',
    { 
        messageId: messageId 
    }, 
    function(returnData)
    {
        getNewMessageCount();
    }, 'json');
}
function deleteSelectedMessages()
{
    var selectedTabIndex = messageTabs.tabs('option', 'selected');
    var selectedMessageIds = "";
    if(selectedTabIndex === 0)
        $("#messageInboxTable .messageInboxSelectBox:checked").each(function() { selectedMessageIds += $(this).attr("id") + ","; });
    else if(selectedTabIndex == 1)
        $("#messageSentTable .messageSentSelectBox:checked").each(function() { selectedMessageIds += $(this).attr("id") + ","; });
    else
        generatePseudoResponse("deleting messages", "Invalid context (inbox or sent).", false);
    if(selectedMessageIds !== "")
        deleteMessage(selectedMessageIds);
    else
        generatePseudoResponse("deleting messages", "Select message(s) for deletion.", false);
}
function deleteMessage(messageId)
{
    $.post(FILELOCKER_ROOT+'/message_interface/delete_messages?format=json', 
    {
        messageIds: messageId
    }, 
    function(returnData) 
    {
        showMessages(returnData, "deleting message");
        viewMessages();
    }, 'json');
}

// Edit Account
function updateUser(userId)
{
    var runUpdate = true;
    var emailRegEx = /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,4}$/i;
    if($("#userPassword").val() != $("#userConfirmPassword").val())
    {
        generatePseudoResponse("updating user account", "Passwords do not match.", false);
        runUpdate = false;
    }
    if($("#userEmail").val() !== "" && $("#userEmail").val().search(emailRegEx) == -1)
    {
        generatePseudoResponse("updating user account", "Email address is not valid.", false);
        runUpdate = false;
    }
    if(runUpdate)
    {
        var updateOptions = {};
        updateOptions.userId = userId;
        if ($("#userPassword").val() !== "")
        {
            updateOptions.password = $("#userPassword").val();
            updateOptions.confirmPassword =  $("#userConfirmPassword").val();
        }
        updateOptions.emailAddress = $("#userEmail").val();
        $.post(FILELOCKER_ROOT+'/user_interface/update_user?format=json',updateOptions, 
        function(returnData) 
        {
            showMessages(returnData, "update user account");
            $("#editAccountBox").dialog("close");
        }, 'json');
    }
}

//CLI
function createCLIKey()
{
    if($("#CLIKeyHostIP").val().match(/^\b(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b$/))
    {
        $.post(FILELOCKER_ROOT+'/cli_interface/create_CLIkey?format=json', 
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
        $.post(FILELOCKER_ROOT+'/cli_interface/create_CLIkey?format=json', 
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
        generatePseudoResponse("creating CLI key", "Not a valid IPv4 or IPv6 address.", false);
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
    $.post(FILELOCKER_ROOT+'/cli_interface/get_CLIkey_list?format=json', 
    {}, 
    function(returnData) 
    {
        var html = "";
        $.each(returnData.data, function(index, value) {
            var hostIP = (value.hostIPv6 === "") ? value.hostIPv4 : value.hostIPv6;
            html += "<tr id='"+index+"_CLIKey' class='groupRow'><td></td><td>"+hostIP+"</td><td>"+value.value+"</td>";
            html += "<td><a href='javascript:regenerateCLIKey(\""+hostIP+"\");' class='inlineLink' title='Regenerate CLI key for this host'><span class='refresh'>&nbsp;</span></a>";
            html += "<form style='display:inline;' action='"+FILELOCKER_ROOT+"/cli_interface/download_CLIconf' method='POST' id='downloadCLIConf_"+value.value+"'><a href='javascript:$(\"#downloadCLIConf_"+value.value+"\").submit()' class='inlineLink' title='Download CLI configuration file for this host'><span class='save'>&nbsp;</span></a><input type='hidden' name='CLIKey' value='"+value.value+"'/></form>";
            html += "<a href='javascript:deleteCLIKey(\""+hostIP+"\");' class='inlineLink' title='Delete CLI key for this host'><span class='cross'>&nbsp;</span></a></td>";
            html += "</tr>";
        });
        if(html === "")
            html = "<tr><td></td><td><i>You have not generated any CLI keys.</i></td><td></td><td></td><td></td></tr>";
        $("#CLIKeyTable").append(html);
        $("#CLIKeyTableSorter").trigger("update");
        $("#CLIKeyTableSorter").trigger("sorton",[[[1,0]]]);
        tipsyfy();
    }, 'json');
}
function deleteCLIKey(hostIP)
{
    if(hostIP.match(/\b(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b/))
    {
        $.post(FILELOCKER_ROOT+'/cli_interface/delete_CLIkey?format=json', 
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
        $.post(FILELOCKER_ROOT+'/cli_interface/delete_CLIkey?format=json', 
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
        $.post(FILELOCKER_ROOT+'/cli_interface/delete_CLIkey?format=json', 
        {
            hostIPv4: "",
            hostIPv6: ""
        }, 
        function(returnData) 
        {
            getCLIKeyList();
        }, 'json');
    }
}

//Roles
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
    var params = {};
    if(roleUserId !== null && roleUserId !== undefined)
        params = { roleUserId: roleUserId };
    $.post(FILELOCKER_ROOT+'/user_interface/switch_roles?format=json', 
    params, 
    function(returnData) 
    {
        location.reload(true);
    }, 'json');
}

// Miscellaneous
function sawBanner()
{
    $.get(FILELOCKER_ROOT+'/saw_banner');
}

/***DOM Ready***/
jQuery(document).ready(function() {
    $("#availableRoles div").css('width', $("#nameRoleContainer").width()+2);
//     $.tablesorter.defaults.headers = {0: {sorter: false}, 4: {sorter: false}};
    $("#quotaProgressBar").progressbar({value:0});
    $("#editAccountBox").dialog($.extend({}, modalDefaults, {
        title: "<span class='gear'>Edit Account</span>",
        width: popup_small_width
    }));
    $("#messagesBox").dialog($.extend({}, modalDefaults, {
        title: "<span class='message'>Messages</span>",
        width: popup_large_width
    }));
    $("#createMessageBox").dialog($.extend({}, modalDefaults, {
        title: "<span class='new_message'>Create Message</span>",
        width: popup_large_width
    }));
    $("#confirmBox").dialog($.extend({}, modalDefaults, {
        title: "<span class='alert'>Confirm Action</span>",
        width: 350,
        buttons: {
            "Cancel": function() { $(this).dialog("close"); },
            "OK": function() { 
                window[$(this).data("funcData").func]($(this).data("funcData").params);
                $(this).dialog("close");
            }
        }
    }));
    $("#account_sections").tabs();
    $("#fileStatistics").tabs();
    $("#CLIKeyTableSorter").tablesorter({
        headers: {
            0: {sorter: false},
            1: {sorter: 'ipAddress'},
            2: {sorter: 'text'},
            3: {sorter: false}
        }
    });
    
    // Messages
    messageTabs = $("#message_sections").tabs();
    $("#message_sections").bind("tabsselect", function(event, ui) {
        $("#selectAllMessageInbox").prop("checked", false);
        $("#selectAllMessageSent").prop("checked", false);
        $("#messageInboxTable .messageInboxSelectBox:checked").each(function() { $(this).prop("checked", false); });
        $("#messageSentTable .messageSentSelectBox:checked").each(function() { $(this).prop("checked", false); });
    });
    $("#messageInboxTableSorter").tablesorter({
        headers: {
            0: {sorter: false},
            1: {sorter: 'text'},
            2: {sorter: 'text'},
            3: {sorter: 'shortDate'},
            4: {sorter: false}
        }
    });
    $("#messageSentTableSorter").tablesorter({
        headers: {
            0: {sorter: false},
            1: {sorter: 'text'},
            2: {sorter: 'text'},
            3: {sorter: 'shortDate'},
            4: {sorter: false}
        }
    });
    
    // Keyboard Shortcuts
    if($.browser.mozilla)
    {
        $("html").keypress(function(e) {
            var element;
            if(e.target) element=e.target;
            else if(e.srcElement) element=e.srcElement;
            if(element.nodeType==3) element=element.parentNode;
            if(element.tagName == 'INPUT' || element.tagName == 'TEXTAREA' || e.ctrlKey || e.altKey || e.metaKey) return;
            var code = e.charCode || e.which || e.keyCode;
            if (code == 97)  { loadEditAccount(); }     // A
            if (code == 102) { loadMyFiles(); }         // F
            if (code == 103) { loadManageGroups(); }    // G
            if (code == 104) { loadHistory(); }         // H
            if (code == 109) { viewMessages(); }        // M
            if (code == 120) { dismissStatusMessage(); }// X
        });
    }
    else
    {
        $("html").keydown(function(e) {
            var element;
            if(e.target) element=e.target;
            else if(e.srcElement) element=e.srcElement;
            if(element.nodeType==3) element=element.parentNode;
            if(element.tagName == 'INPUT' || element.tagName == 'TEXTAREA' || e.ctrlKey || e.altKey || e.metaKey) return;
            var code = e.charCode || e.which || e.keyCode;
            if (code == 65) { loadEditAccount(); }     // A
            if (code == 70) { loadMyFiles(); }         // F
            if (code == 71) { loadManageGroups(); }    // G
            if (code == 72) { loadHistory(); }         // H
            if (code == 77) { viewMessages(); }        // M
            if (code == 88) { dismissStatusMessage(); }// X
        });
    }
    
    // Uploader
    $("#statusMessage").ajaxError(function(e, xhr, settings, exception) {
        var message = (xhr.status >= 400) ? "Server returned code "+xhr.status : "No details.";
        clearInterval(messagePoller); 
        generatePseudoResponse("requesting data", message, false);
    });
    initFiles();
    if (BANNER)
    {
        $("#bannerBox").dialog($.extend({}, modalDefaults, {
            title: "<span class='help'>Message from the Administrator:</span>",
            width: popup_small_width
        }));
        $("#bannerBox").dialog("open");
    }
    getNewMessageCount();
    //messagePoller = setInterval(function() { getNewMessageCount(); }, 30000); //TODO Move this into poller with UpdateQuota
    checkServerMessages("loading page");
});
