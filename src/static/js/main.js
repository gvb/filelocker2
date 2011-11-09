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
    *       verboseMode (bool):         Determines whether to show a success message if the request completes and there are no failure messages from the server.
    *       successFunction (function): OPTIONAL callback function to execute if the request completes.
    */
    function request(path, action, payloadObject, verboseMode, successFunction)
    {
        console.log("Start \tN/A\tverbose:" + verboseMode + "\t" + action);
        $.ajax({
            type: "POST",
            cache: false,
            dataType: "json",
            url: FILELOCKER_ROOT + path,
            data: payloadObject,
            success: function(response) {
                console.log("End \t" + 200 + "\tverbose:" + verboseMode + "\t" + action);
                if (response.fMessages.length > 0) {
                    console.error(action + " " + response.fMessages);
                    StatusResponse.show(response, action);
                }
                else if (verboseMode)
                    StatusResponse.show(response, action);
                if (typeof (successFunction) === "function")
                    successFunction.call(this, response)
            },
            error: function(response, status, error) {
                console.log("End \t" + status + "\tverbose:" + verboseMode + "\t" + action);
                StatusResponse.create(action, response.status + " " + status + ": " + error, false);
            }
        });
    }

    function login()
    {
        window.location.replace(FILELOCKER_ROOT);
    }
    
    function sawBanner()
    {
        Filelocker.request("/saw_banner", "reading banner", "{}", false);
    }

    function checkMessages(actionName)
    {
        Filelocker.request("/get_server_messages", actionName, "{}", false);
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
        checkMessages:checkMessages,
        selectAll:selectAll
    };
}();
