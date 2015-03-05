History = function() {
    function init()
    {
        $("input.datePast").datepicker("destroy").datepicker({dateFormat: 'mm/dd/yy', maxDate: 0});
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
    function load()
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
                StatusResponse.create("loading history page", "Error "+xhr.status+": "+xhr.textStatus, false);
            else 
            {
                if ($("#sessionState").length >0 && $("#sessionState").val() == "expired")
                    Filelocker.login();
                else
                    init();
            }
            if($("#adminBackLink"))
                $("#adminBackLink").html("<div id='adminLink' class='settings'><a href='javascript:Admin.load()' title='Launch the admin panel'>Admin</a></div>");
            Utility.tipsyfy();
        });
    }
    
    return {
        load:load
    }
}();