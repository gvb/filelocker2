var uploader;

//File List
function initPublicUpload()
{
    $("#password").val("");
    $(".dateFuture").datepicker({dateFormat: 'mm/dd/yy', constrainInput: true, minDate: 0});
    if($("#uploadButton")[0])
    {
        uploader = new qq.FileUploader({
            element: $("#uploadButton")[0],
            listElement: $("#progressBarSection")[0],
            action: FILELOCKER_ROOT+'/file_interface/upload?format=json',
            params: {},
            sizeLimit: 2147483647,
            onSubmit: function(id, fileName){
                var uploadOptions = {};
                if ($("#puScanFile").attr("checked"))
                    uploadOptions.scanFile = "yes";
                else
                    uploadOptions.scanFile = "no";
                uploadOptions.fileNotes= $("#fileNotes").val();
                uploadOptions.expiration = $("#puExpiration").val();
                uploadOptions.uploadIndex = id;
                uploader.setParams(uploadOptions);
                $("#uploadBox").dialog("close");
                continuePolling = true;
                if(pollerId === "")
                    pollerId = setInterval(function() { poll(); }, 1000);
            },
            onProgress: function(id, fileName, loaded, total){
                checkServerMessages("uploading file");
            },
            onComplete: function(id, fileName, response){
                var serverMsg = checkServerMessages("uploading file");
                if(!serverMsg)
                    showMessages(response, "uploading file");
                refreshFileList();
            },
            onCancel: function(id, fileName){
                generatePseudoResponse("cancelling upload", "File upload cancelled by user.", true);
            },
            messages: {
                sizeError: "sizeError"
            },
            showMessage: function(message){
                if(message === "sizeError")
                {
                    var browserAndVersion = detectBrowserVersion();
                    generatePseudoResponse("uploading large file", "Your browser ("+browserAndVersion[0]+" "+browserAndVersion[1]+") does not support large file uploads.  Click <span id='helpUploadLarge' class='helpLink'>here</span> for more information.", false);
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
function refreshFileList()
{
    $("#wrapper_col1").load(FILELOCKER_ROOT+"/public_upload?format=content_only&ms=" + new Date().getTime(), {}, function (responseText, textStatus, xhr) {
        initPublicUpload();
    });
}
function verifyUploadTicket()
{
    $("#verifyTicketForm").submit();
}
jQuery(document).ready(function(){
    initPublicUpload();
});