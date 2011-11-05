Filelocker = function(){
    var statFile = "";
    var messageTabs;
    var messagePoller;
    var uploader;

    /*
    *   Description: Abstraction for handling AJAX requests.
    *   Parameters:
    *       path (string):              Service function to call (with leading slash).
    *       action (string):            String for success/error messages in form of "[update or refresh]ing [section of valuation]".
    *       payloadObject (object):     Object to be consumed by endpoint.
    *       showMessage (bool):         Determines whether to show a message if the request completes.
    *       successFunction (function): OPTIONAL callback function.
    */
    function request(path, action, payloadObject, showMessage, successFunction)
    {
        $.ajax({
            type: "POST",
            cache: false,
            dataType: "json",
            url: FILELOCKER_ROOT + path,
            data: payloadObject,
            success: function(response) {
                if (showMessage)
                    StatusResponse.show(response, action);
                if (typeof (successFunction) === "function")
                    successFunction.call(this, response)
            },
            error: function(response, status, error) {
                generateMessage(action, response.status + " " + status + ": " + error, false);
            }
        });
    }

    function login()
    {
        window.location.replace(FILELOCKER_ROOT);
    }
    
    function sawBanner()
    {
        Filelocker.request("/saw_banner", "", "{}", false);
    }

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

    return {
        statFile:statFile,
        messageTabs:messageTabs,
        messagePoller:messagePoller,
        uploader:uploader,
        request:request,
        login:login,
        sawBanner:sawBanner,
        selectAll:selectAll
    };
}();

jQuery(document).ready(function() {
    $("#availableRoles div").css('width', $("#nameRoleContainer").width()+2);
//     $.tablesorter.defaults.headers = {0: {sorter: false}, 4: {sorter: false}};
    $("#quotaProgressBar").progressbar({value:0});
    $("#editAccountBox").dialog($.extend({}, Defaults.largeDialog, {
        title: "<span class='gear'>Edit Account</span>"
    }));
    $("#messagesBox").dialog($.extend({}, Defaults.largeDialog, {
        title: "<span class='message'>Messages</span>"
    }));
    $("#createMessageBox").dialog($.extend({}, Defaults.largeDialog, {
        title: "<span class='new_message'>Create Message</span>"
    }));
    $("#confirmBox").dialog($.extend({}, Defaults.smallDialog, {
        title: "<span class='alert'>Confirm Action</span>",
        width: 350,
        buttons: {
            "Cancel": function() { $(this).dialog("close"); },
            "OK": function() {
                //TODO assumes Namespace.function
                var funcParts = $(this).data("funcData").func.split(".");
                window[funcParts[0]][funcParts[1]]($(this).data("funcData").params);
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
            if (code == 97)  Account.load();        // A
            if (code == 102) FLFile.load();           // F
            if (code == 103) Group.load();          // G
            if (code == 104) History.load();        // H
            if (code == 109) Message.view();        // M
            if (code == 120) StatusResponse.hide(); // X
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
            if (code == 65) Account.load();        // A
            if (code == 70) FLFile.load();           // F
            if (code == 71) Group.load();          // G
            if (code == 72) History.load();        // H
            if (code == 77) Message.view();        // M
            if (code == 88) StatusResponse.hide(); // X
        });
    }
    
    // Uploader
    $("#statusMessage").ajaxError(function(e, xhr, settings, exception) {
        var message = (xhr.status >= 400) ? "Server returned code "+xhr.status : "No details.";
        clearInterval(Filelocker.messagePoller); 
        StatusResponse.create("requesting data", message, false);
    });
    FLFile.init();
    if (BANNER)
    {
        $("#bannerBox").dialog($.extend({}, Defaults.smallDialog, {
            title: "<span class='help'>Message from the Administrator:</span>"
        }));
        $("#bannerBox").dialog("open");
    }
    Message.getCount();
    Filelocker.messagePoller = setInterval(function() { Message.getCount(); }, 30000); //TODO Move this into poller with UpdateQuota
    checkServerMessages("loading page");
});
