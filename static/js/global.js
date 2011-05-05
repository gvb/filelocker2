var pollerId="";
var messageTimer;
var continuePolling = false;
var popup_small_width = 580;
var popup_large_width = 780;
var filelocker_width = 870;
var modalDefaults = {
    autoOpen: false,
    draggable: false,
    modal: true,
    resizable: false,
    zIndex: 10
};

function login()
{
    window.location.replace(FILELOCKER_ROOT);
}
function toggleDetails(toggleAction)
{
    clearTimeout(messageTimer);
    if (toggleAction =="show")
    {
        $("#statusMessageDetails").show();
        $("#showDetailsLink").hide();
        $("#hideDetailsLink").show();
        $("#hideDetailsLink").addClass("statusMessageDetailsLink");
    }
    else if (toggleAction =="hide")
    {
        $("#statusMessageDetails").hide();
        $("#hideDetailsLink").hide();
        $("#showDetailsLink").show();
        $("#showDetailsLink").addClass("statusMessageDetailsLink");
    }
}
function dismissStatusMessage()
{
    if($("#statusMessage").is(":visible"))
    {
        toggleDetails("hide");
        $("#statusMessage").hide("drop", { direction: "up" }, 200);
    }
}
function showMessages(response, shortActionMessage)
{
    var options = {};
    var detailSection ="<span id=\"statusMessageDetails\" class=\"hidden\"><p class='errorDetails'><strong>Details:&nbsp;</strong>";
    $.each(response.fMessages, function(index,value) {
        if (value == "expired")
            login();
        else
            detailSection += value + "<br />";
    });
    $.each(response.sMessages, function(index,value) {
        detailSection += value + "<br />";
    });
    detailSection += "</p></span>";
    if (response.fMessages !== undefined && response.fMessages.length > 0) // Errors occurred, aggregate messages and permanently display.
    {
        $("#statusMessage").removeClass("ui-state-highlight");
        $("#statusMessage").addClass("ui-state-error");
        $("#statusMessage").html("<span class='ui-icon ui-icon-alert' style='float: left; margin-right: .3em'></span>Errors while "+shortActionMessage+" <span id='toggleDetails'><span id='showDetailsLink' class='statusMessageDetailsLink'>(show details) </span><span id='hideDetailsLink' class='statusMessageDetailsLink hidden'>(hide details) </span></span><span id='dismissStatusMessage' style='float: right;'><span class='dismiss'></span></span>"+detailSection);
        $("#statusMessage").show("drop", { direction: "up" }, 200);
    }
    else // No errors, so just display success, and fade away after 5 seconds.
    {
        $("#statusMessage").removeClass("ui-state-error");
        $("#statusMessage").addClass("ui-state-highlight");
        $("#statusMessage").html("<span class='ui-icon ui-icon-check' style='float: left; margin-right: .3em'></span>Success "+shortActionMessage+" <span id='toggleDetails'><span id='showDetailsLink' class='statusMessageDetailsLink'>(show details) </span><span id='hideDetailsLink' class='statusMessageDetailsLink hidden'>(hide details) </span></span><span id='dismissStatusMessage' style='float: right;'><span class='dismiss'></span></span>"+detailSection);
        $("#statusMessage").show("drop", { direction: "up" }, 200);
        messageTimer = setTimeout(function() { dismissStatusMessage(); }, 5000);
    }
}
function generatePseudoResponse(action, message, success)
{
    var pseudoResponse = Array();
    pseudoResponse.sMessages = [];
    pseudoResponse.fMessages = [];
    var msgArray = success ? pseudoResponse.sMessages : pseudoResponse.fMessages;
    msgArray.push(message);
    showMessages(pseudoResponse, action);
}
function checkServerMessages(actionName)
{
    $.getJSON(FILELOCKER_ROOT+'/get_server_messages?format=json&ms=' + new Date().getTime(), function(response) {
        if (response.fMessages.length > 0 || response.sMessages.length > 0)
            showMessages(response, actionName);
        else
            return false;
    });
}
function limitCharacters(destination)
{
    var characterLimit = 250;
    var currentText = "";
    var textId = "";
    var notesId = "";
    if(destination == "upload")
    {
        textId = "uploadFileNotes";
        notesId = "uploadNotesInfo";
    }
    else if(destination == "public_upload")
    {
        textId = "fileNotes";
        notesId = "publicUploadNotesInfo";
    }
    else if(destination == "upload_request")
    {
        characterLimit = 1000;
        textId = "uploadRequestMessage";
        notesId = "uploadRequestNotesInfo";
    }
    else if(destination == "messages")
    {
        characterLimit = 1000;
        textId = "flMessageBody";
        notesId = "messageInfo";
    }
    if($("#"+textId).val().length > characterLimit)
    {
        $("#"+notesId).html("You are unable to write more than "+characterLimit+" characters.");
        $("#"+textId).val($("#"+textId).val().substr(0, characterLimit));
        return false;
    }
    else
    {
        $("#"+notesId).html("You have "+ (characterLimit - $("#"+textId).val().length) +" characters remaining.");
        return true;
    }
}
function detectBrowserVersion(){
    var userAgent = navigator.userAgent.toLowerCase();
    $.browser.chrome = /chrome/.test(navigator.userAgent.toLowerCase());
    var version = 0;
    var browserName = "";

    // Is this a version of IE?
    if($.browser.msie) {
        userAgent = $.browser.version;
        userAgent = userAgent.substring(0,userAgent.indexOf('.'));  
        version = userAgent;
        browserName = "Internet Explorer";
    }

    // Is this a version of Chrome?
    if($.browser.chrome) {
        userAgent = userAgent.substring(userAgent.indexOf('chrome/') +7);
        userAgent = userAgent.substring(0,userAgent.indexOf('.'));  
        version = userAgent;
        // If it is chrome then jQuery thinks it's safari so we have to tell it it isn't
        $.browser.safari = false;
        browserName = "Chrome";
    }

    // Is this a version of Safari?
    if($.browser.safari) {
        userAgent = userAgent.substring(userAgent.indexOf('safari/') +7);   
        userAgent = userAgent.substring(0,userAgent.indexOf('.'));
        version = userAgent;
        browserName = "Safari";
    }

    // Is this a version of Mozilla?
    if($.browser.mozilla) {
        //Is it Firefox?
        if(navigator.userAgent.toLowerCase().indexOf('firefox') != -1) {
            userAgent = userAgent.substring(userAgent.indexOf('firefox/') +8);
            userAgent = userAgent.substring(0,userAgent.indexOf('.'));
            version = userAgent;
            browserName = "Firefox";
        }
        // If not then it must be another Mozilla
    }

    // Is this a version of Opera?
    if($.browser.opera) {
        userAgent = userAgent.substring(userAgent.indexOf('version/') +8);
        userAgent = userAgent.substring(0,userAgent.indexOf('.'));
        version = userAgent;
        browserName = "Opera";
    }
    return [browserName, version];
}
function check(checkboxId)
{
    if($("#"+checkboxId).is(":checked"))
        $("#"+checkboxId).prop("checked", false);
    else
        $("#"+checkboxId).prop("checked", true);
}
function allClassBoxChecked(checkboxId, classIdent)
{
    if ($("#"+checkboxId).is(":checked"))
        $("."+classIdent).prop("checked", true);
    else
        $("."+classIdent).prop("checked", false);
}
function poll()
{
    if(continuePolling)
    {
        continuePolling = false;
        $.getJSON(FILELOCKER_ROOT+'/file_interface/upload_stats?format=json&ms=' + new Date().getTime(), function(uploadStats) {
            continuePolling = true;
            if(uploadStats === null || typeof(uploadStats.data) == 'undefined' || uploadStats.data.length === 0) // Files are done uploading
            {
                $(".progress_row").each(function(index) { $(this).remove(); });
                clearInterval(pollerId);
                pollerId = "";
            }
            else if (uploadStats === null) { continuePolling = false; } // This usually means the webserver has died
            else // Files are still uploading
            {
                var maxEta = 0;
                var maxEtaTimeSuffix = "seconds";
                var totalPercent = 0;
                //TODO: Rewrite using $.each
                for(var x=0; x < uploadStats.data.length; x++)
                {
                    var suffix = "kB";
                    var fileStatus = uploadStats.data[x].status;
                    var uploaded = uploadStats.data[x].transferredKB;
                    var total = parseFloat(uploadStats.data[x].sizeKB);
                    var percent = (uploaded/total)*100;
                    while (total>1024)
                    {
                        if (suffix == "kB")
                            suffix = "MB";
                        else if (suffix == "MB")
                            suffix = "GB";
                        total /= 1024;
                    }
                    var eta = uploadStats.data[x].eta;
                    if (maxEta < eta)
                        maxEta = eta;
                    var timeSuffix = "seconds";
                    if (eta > 60) 
                    {
                        eta = eta/60;
                        if(Math.floor(eta) != 1)
                            timeSuffix = "minutes";
                        else
                            timeSuffix = "minute";
                    }
                    if (eta > 60)
                    {
                        eta = eta/60;
                        if(Math.floor(eta) != 1)
                            timeSuffix = "hours";
                        else
                            timeSuffix = "hour";
                    }
                    
                    totalPercent += percent;
                    var fileName = uploadStats.data[x].fileName;
                    if(fileName.length > 50)
                        fileName = fileName.substring(0,25) + "..." + fileName.substring(fileName.length-10,fileName.length);
                    var speed = uploadStats.data[x].speed;
                    var uIndex = uploadStats.data[x].uploadIndex;
                    percent = parseInt(percent, 10);
                    var rowId = "upload_" + x;
                    eta = parseInt(eta, 10).toFixed(0);
                    if ($("#"+rowId).length > 0)
                    {
                        $("#"+rowId).progressbar("value", percent);
                        $("#"+rowId+" >div").html("<span class='document progressBarText' title='"+fileName+": "+Math.round(uploaded)+" kB of "+Math.round(total)+" "+suffix+" transferred at "+Math.round(speed)+" kBps'>"+fileName+": "+fileStatus+"</span>");
                        $("#"+rowId+"_eta").html(eta+" "+timeSuffix);
                        if(fileStatus == "Scanning and Encrypting" || fileStatus == "Encrypting")
                        {
                            $("#"+rowId+"_cancel").empty();
                            $("#"+rowId).progressbar("value", 100);
                            $("#"+rowId+" >div.ui-progressbar-value").css("background-image","url("+FILELOCKER_ROOT+"/static/images/pbar-ani.gif)");
                        }
                    }
                    else
                    {
                        var totalToDisplay = 0;
                        if(suffix != "GB")
                            totalToDisplay = total.toFixed(0);
                        else
                            totalToDisplay = total.toFixed(2);
                        $("#progressBarSection").append("<tr class='progress_row'><td></td><td><div class='progressbarDoc'></div><div id='"+rowId+"'></div></td><td>"+totalToDisplay+" "+suffix+"</td><td id='"+rowId+"_eta'>"+eta+" "+timeSuffix+"</td><td id='"+rowId+"_cancel'><a href='javascript:uploader._handler.cancel("+uIndex+");' class='inlineLink' title='Cancel File Upload'><span class='cross'>&nbsp;</span></a></td></tr>"); 
                        $("#"+rowId).progressbar({value:percent});
                        $("#"+rowId+" >div").html("<span class='document progressBarText' title='"+fileName+": "+Math.round(uploaded)+" kB of "+Math.round(total)+" "+suffix+" transferred at "+Math.round(speed)+" kBps'>"+fileName+": "+fileStatus+"</span>");
                        if(fileStatus == "Scanning and Encrypting" || fileStatus == "Encrypting")
                        {
                            $("#"+rowId+"_cancel").empty();
                            $("#"+rowId).progressbar("value", 100);
                            $("#"+rowId+" >div.ui-progressbar-value").css("background-image","url("+FILELOCKER_ROOT+"/static/images/pbar-ani.gif)");
                        }
                    }
                }
            }
        });
    }
}
// Help
function loadHelp()
{
    var html = "";
    var oddRow = "oddRow";
    var count = 1;
    $("#helpViewer").load(FILELOCKER_ROOT+"/help?ms=" + new Date().getTime(), {}, function (responseText, textStatus, xhr) {
        if (textStatus == "error")
            generatePseudoResponse("loading help", "Error "+xhr.status+": "+xhr.textStatus, false);
        else
        {
            $("#helpViewer > div").each(function(index, value) {
                $(this).hide();
                oddRow = (count%2 === 0) ? "" : "oddRow";
                html += "<tr id='"+$(this).attr("id")+"_row' class='fileRow "+oddRow+"' onClick='javascript:openHelp(\""+$(this).attr("id")+"\");'><td class='leftborder'></td><td class='rightborder pseudoLink'>" + $(this).children("h4").html() + "</td></tr>";
                count++;
            });
            $("#helpTableOfContents").html(html);
            getRandomTip();
        }
    });
}
function viewHelp(subject)
{
    tipsyfy();
    $("#helpBox").dialog("open");
    if(subject !== undefined)
        openHelp(subject);
    else
        openHelp("help_start");
}
function openHelp(subject)
{
    $("#helpTableOfContents tr").each(function(index, value) {
        $(this).removeClass("rowSelected");
    });
    $("#"+subject+"_row").addClass("rowSelected");
    $("#helpViewer > div").each(function(index, value) {
        $(this).hide();
    });
    $("#"+subject).show();
}

// Miscellaneous
function getRandomTip()
{
    var tip = $("#help_just_the_tips li:random").text();
    $("#randomTip").text(tip);
}
function tipsyfy()
{
    $(".tipsy").remove(); // Remove any currently displayed tipsy elements.
    $("a").filter(function() { // Add the external link class to the tipsy for all external links (including mailto).
        if((this.hostname && this.hostname !== location.hostname && $(this).attr("title")) || this.href.match(/^mailto\:/))
            $(this).attr("title","<span class='external'>" + $(this).attr("title") + "</span>");
    });
    $("a, #quotaProgressBar, #fileVaultUsageBar, #nameRoleContainer div, .publicShareCheckbox, .notifyCheckbox, .groupMember, .groupName, .attributeName, .userQuotaUsage").tipsy({ // Initiate tipsy for all links, progress bars, and some custom elements
        delayIn: 500,
        gravity: 'nw',
        html: true,
        opacity: 0.9
    });
}
function toggleTypography(){var y="body, p, h1, h2, h3, h4, h5, h6, a, thead, th, td, ol, ul, li, dt, dd, sub, sup, label, fieldset, form";if($.browser.mozilla)var z="\"Lucida Grande\",\"Segoe UI\",Arial,Verdana,sans-serif";else var z="'Lucida Grande', 'Segoe UI', Arial, Verdana, sans-serif";if($("body").css("font-family")==z||$("body").css("font-family")==z)$(y).css("font-family","\"Comic Sans MS\"");else $(y).css("font-family",z);}
jQuery.jQueryRandom = 0;
jQuery.extend(jQuery.expr[":"],
{
    random: function(a, i, m, r) {
        if (i == 0) {
            jQuery.jQueryRandom = Math.floor(Math.random() * r.length);
        };
        return i == jQuery.jQueryRandom;
    }
});
jQuery.fn.scrollToTop = function () {
    $("html, body").animate({
        scrollTop: $("#background").offset().top
    }, 1500);
    return this;
};
jQuery(document).ready(function(){
    if($.tablesorter)
    {
        $.tablesorter.defaults.widgets = ['zebra'];
        $.tablesorter.addParser({
            id: 'fileSize',
            is: function(s) { 
                return s.match(new RegExp( /[0-9]+(\.[0-9]+)?\ (kB|B|MB|GB|TB)/ )); 
            },
            format: function(s) {
                var suf = s.match(new RegExp( /(kB|B|MB|GB|TB)$/ ))[1];
                var num = parseFloat(s.match(new RegExp( /^[0-9]+(\.[0-9]+)?/ ))[0]);
                switch(suf) {
                    case 'B':
                        return num * Math.pow(1024,0);
                    case 'kB':
                        return num * Math.pow(1024,1);
                    case 'MB':
                        return num * Math.pow(1024,2);
                    case 'GB':
                        return num * Math.pow(1024,3);
                    case 'TB':
                        return num * Math.pow(1024,4);
                    default:
                        return 0;
                }
            },
            type: 'numeric'
        });
    }
    
    // Bind events to status message events and overlay clicks so they can pierce the jQuery UI modal overlay.
    $("#showDetailsLink").live("click", function() {
        toggleDetails("show");
    });
    $("#hideDetailsLink").live("click", function() {
        toggleDetails("hide");
    });
    $("#dismissStatusMessage").live("click", function() {
        dismissStatusMessage();
    });
    $("#helpUploadLarge").live("click", function() {
        viewHelp("help_upload_large");
    });
    $(".ui-widget-overlay").live("click", function() {
        $(".ui-dialog:visible").find(".ui-dialog-titlebar-close").trigger('click');
    });
    
    // Load help documentation for all public and private pages.
    loadHelp();
    $("#helpBox").dialog($.extend({}, modalDefaults, {
        title: "<span class='help'>Help</span>",
        width: popup_large_width
    }));
    
    // Implementation of string trimming for IE.
    if(typeof String.prototype.trim !== 'function') {
        String.prototype.trim = function() {
            return this.replace(/^\s+|\s+$/g, ''); 
        };
    }
    
    tipsyfy();
    $("#footer p").html($("#footer p").html().replace("©","<span onclick='javascript:toggleTypography();'>&copy;</span>"));
});