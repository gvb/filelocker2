PublicUpload = function() {
    var uploader;
    function init()
    {
        $("#password").val("");
        $(".dateFuture").datepicker({dateFormat: 'mm/dd/yy', constrainInput: true, minDate: 0});
        if($("#uploadButton")[0])
        {
            uploader = new qq.FileUploader({
                element: $("#uploadButton")[0],
                listElement: $("#progressBarSection")[0],
                action: FILELOCKER_ROOT+'/file/upload',
                params: {},
                //sizeLimit: 2147483647,
                onSubmit: function(id, fileName){
                    uploader.setParams({
                        scanFile: $("#puScanFile").prop("checked"),
                        fileNotes: $("#puFileNotes").val(),
                        expiration: $("#puExpiration").val(),
                        uploadIndex: id,
                        fileName: fileName
                    });
                    $("#uploadBox").dialog("close");
                    continuePolling = true;
                    if(pollerId === "")
                        pollerId = setInterval(function() { poll(); }, 1000);
                },
                onComplete: function(id, fileName, response){
                    location.reload(true);
                },
                onCancel: function(id, fileName){
                    StatusResponse.create("cancelling upload", "File upload of " + fileName + " cancelled by user.", true);
                },
                messages: {
                    sizeError: "sizeError"
                },
                showMessage: function(message){
                    if(message === "sizeError")
                    {
                        var browserAndVersion = Utility.detectBrowserVersion();
                        StatusResponse.create("uploading large file", "Your browser ("+browserAndVersion[0]+" "+browserAndVersion[1]+") does not support large file uploads.  Click <span id='helpUploadLarge' class='helpLink'>here</span> for more information.", false);
                    }
                }
            });
        }
        if($("#filesTable tr").length > 0)
        {
            $("#fileTableSorter").tablesorter({
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
    }
    function load()
    {
        //todo no .load
        $("#wrapper_col1").load(FILELOCKER_ROOT+"/public_upload?format=content_only&ms=" + new Date().getTime(), {}, function (responseText, textStatus, xhr) {
            init();
        });
    }
    
    return {
        init:init,
        load:load
    };
}();
jQuery(document).ready(function(){
    PublicUpload.init();
});
