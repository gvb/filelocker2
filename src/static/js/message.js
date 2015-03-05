Message = function() {
    function load()
    {
        var action = "retrieving messages";
        Filelocker.request("/message/get_messages", action, "{}", false, function(returnData) {
            if(returnData.data.length == 0)
            {
                StatusResponse.create(action, "No messages found.", false);
                return false;
            }

            var recvhtml = "";
            $.each(returnData.data[0], function(index, value) {
                var unreadMessage = (value.viewedDatetime === null) ? "unreadMessage" : "";
                var shortenedSubject = (value.subject.length > 30)
                    ? value.subject.substring(0,22) + "..." + value.subject.substring(value.subject.length-5,value.subject.length)
                    : value.subject;
                recvhtml += "<tr id='"+value.id+"_inbox' class='groupRow "+unreadMessage+"' onClick='javascript:Message.read(\""+value.id+"\",\"inbox\");'>";
                recvhtml += "<td class='leftborder'><input id='"+value.id+"' type='checkbox' class='messageInboxSelectBox' /><span id='"+value.id+"_subject' class='hidden'>"+value.subject+"</span><span id='"+value.id+"_body' class='hidden'>"+value.body+"</span></td>";
                recvhtml += "<td><a href='javascript:Message.read(\""+value.id+"\",\"inbox\");' class='messageLink'>"+value.ownerId+"</a></td><td><a class='messageLink' href='javascript:Message.read(\""+value.id+"\",\"inbox\");'>"+shortenedSubject+"</a></td><td>"+value.creationDatetime+"</td><td class='rightborder'><a href='javascript:Message.promptCreateReply(\""+value.subject+"\",\""+value.ownerId+"\");javascript:Account.Search.manual(\""+value.ownerId+"\", \"messages\");' class='inlineLink' title='Reply to this message'><span class='replyMessage'>&nbsp;</span></a><a href='javascript:Utility.promptConfirmation(\"Message.delShare\", [\""+value.id+"\"]);' class='inlineLink' title='Delete this message'><span class='cross'>&nbsp;</span></a></td>";
                recvhtml += "</tr>";
            });
            if(recvhtml === "")
            {
                recvhtml = "<tr><td></td><td><i>No messages.</i></td><td></td><td></td><td></td></tr>";
                $("#messageSubject").html("");
                $("#messageBody").html("<a href='javascript:Help.prompt(\"help_message\");' class='helpLink'>Learn more about Filelocker Messaging.</a>");
            }
            $("#messageInboxTable").append(recvhtml);

            var senthtml = "";
            $.each(returnData.data[1], function(index, value) {
                var shortenedSubject = (value.subject.length > 30)
                    ? value.subject.substring(0,22) + "..." + value.subject.substring(value.subject.length-5,value.subject.length)
                    : value.subject;
                senthtml += "<tr id='"+value.id+"_sent' class='groupRow ' onClick='javascript:Message.read(\""+value.id+"\",\"sent\");'>";
                senthtml += "<td class='leftborder'><input id='"+value.id+"' type='checkbox' class='messageSentSelectBox' /><span id='"+value.id+"_subject' class='hidden'>"+value.subject+"</span><span id='"+value.id+"_body' class='hidden'>"+value.body+"</span></td>";
                senthtml += "<td><a href='javascript:Message.read(\""+value.id+"\",\"sent\");' class='messageLink'>"+value.messageRecipients+"</a></td><td><a href='javascript:Message.read(\""+value.id+"\",\"sent\");' class='messageLink'>"+shortenedSubject+"</a></td><td>"+value.creationDatetime+"</td><td class='rightborder'><a href='javascript:Utility.promptConfirmation(\"Message.del\", [\""+value.id+"\"]);' class='inlineLink' title='Delete this message'><span class='cross'>&nbsp;</span></a></td>";
                senthtml += "</tr>";
            });
            if(senthtml === "")
            {
                senthtml = "<tr><td></td><td><i>No messages.</i></td><td></td><td></td><td></td></tr>";
                $("#messageSubject").html("");
                $("#messageBody").html("<a href='javascript:Help.prompt(\"help_message\");' class='helpLink'>Learn more about Filelocker Messaging.</a>");
            }
            $("#messageSentTable").append(senthtml);

            $("#messageInboxTableSorter").trigger("update");
            $("#messageInboxTableSorter").trigger("sorton",[[[3,1],[2,0]]]);
            $("#messageSentTableSorter").trigger("update");
            $("#messageSentTableSorter").trigger("sorton",[[[3,1],[2,0]]]);

            $("#messagesBoxTitle").removeClass("loading");
            $("#messagesBoxTitle").addClass("messagesTitle");
            $("#messagesBoxTitle").html("Messages");
            Utility.tipsyfy();
            return true;
        });
    }

    function create(recipientIds)
    {
        var action = "sending message";
        var subject = $("#flMessageSubject").val();
        var body = $("#flMessageBody").val();

        if (subject == null || subject === "")
            return StatusResponse.create(action, "Message must have a subject.", false);
        if (body == null || body === "")
            return StatusResponse.create(action, "Message must have a body.", false);
        var data = {
            subject: subject,
            body: body,
            expiration: $("#flMessageExpiration").val(),
            recipientIds: recipientIds
        };
        Filelocker.request("/message/create_message", "sending message", data, true, function() {
            $("#createMessageBox").dialog("close");
            load();
        });
    }

    function read(messageId, context)
    {
        $.each($("#messageInboxTable tr"), function() {
            $(this).removeClass("rowSelected leftborder");
        });
        $.each($("#messageSentTable tr"), function() {
            $(this).removeClass("rowSelected leftborder");
        });
        if(context === "inbox")
        {
            $("#"+messageId+"_inbox").addClass("rowSelected leftborder rightborder");
            $("#"+messageId+"_inbox").removeClass("unreadMessage");
        }
        else
            $("#"+messageId+"_sent").addClass("rowSelected leftborder rightborder");
        $("#messageSubject").html("<span class='messageHeader'>Subject:</span>" + $("#"+messageId+"_subject").text());
        $("#messageBody").html("<hr class='messageViewBreak' /><span class='messageHeader'>Body:</span>" + $("#"+messageId+"_body").text());
        if (context === "inbox") {
            Filelocker.request("/message/read_message", "reading message", { messageId:messageId }, false, function() {
                getCount();
            });
        }
    }
    
    function del(messageId)
    {
        Filelocker.request("/message/delete_messages", "deleting messages", { messageIds:messageId }, true, function() {
            prompt();
        });
    }

    function delShare(messageId)
    {
        Filelocker.request("/message/delete_message_shares", "deleting messages", { messageIds:messageId }, true, function() {
            prompt();
        });
    }

    function prompt()
    {
        $("#selectAllMessageInbox").prop("checked", false);
        $("#selectAllMessageSent").prop("checked", false);
        $("#messageInboxTable").html("");
        $("#messageSentTable").html("");
        $("#messagesBox").dialog("open");
        $("#messagesBoxTitle").removeClass("messagesTitle");
        $("#messagesBoxTitle").addClass("loading");
        $("#messagesBoxTitle").html("Loading...");
        load();
    }
    
    function promptCreate()
    {
        $("#messagesBox").dialog("close");
        $("#flMessageSubject").val("");
        $("#flMessageRecipientId").val("");
        $("#flMessageBody").val("");
        Account.Search.init("messages");
        $("#createMessageBox").dialog("open");
    }

    function promptCreateReply(subject)
    {
        $("#messagesBox").dialog("close");
        if(subject.match(/^RE:/g))
            $("#flMessageSubject").val(subject);
        else
            $("#flMessageSubject").val("RE: " + subject);
        $("#flMessageBody").val("");
        Account.Search.init("messages");
        $("#createMessageBox").dialog("open");
        return false;
    }

    function getCount()
    {
        Filelocker.request("/message/get_new_message_count", "retrieving message unread count", "{}", false, function(returnData)
        {
            var noNewMessages = $("#messagesLink").hasClass("messages");
            if (returnData != null)
            {
                if(returnData.data !== 0)
                {
                    $("#messagesLink").removeClass("messages");
                    $("#messagesLink").addClass("messagesNew");
                    if (returnData.data != null)
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

    function deleteSelected()
    {
        var selectedTabIndex = messageTabs.tabs('option', 'selected');
        var selectedMessageIds = "";
        if(selectedTabIndex === 0)
            $("#messageInboxTable .messageInboxSelectBox:checked").each(function() { selectedMessageIds += $(this).attr("id") + ","; });
        else if(selectedTabIndex === 1)
            $("#messageSentTable .messageSentSelectBox:checked").each(function() { selectedMessageIds += $(this).attr("id") + ","; });
        else
            StatusResponse.create("deleting messages", "Invalid context (inbox or sent).", false);
        if(selectedMessageIds !== "")
            del(selectedMessageIds);
        else
            StatusResponse.create("deleting messages", "Select message(s) for deletion.", false);
    }
    
    return {
        load:load,
        create:create,
        read:read,
        del:del,
        delShare:delShare,
        prompt:prompt,
        promptCreate:promptCreate,
        promptCreateReply:promptCreateReply,
        getCount:getCount,
        deleteSelected:deleteSelected
    };
}();
