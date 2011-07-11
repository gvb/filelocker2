using System;
using MonoTouch.UIKit;
using System.Collections.Generic;
namespace Filelocker
{
	public class FLFile
	{
		public string fileId {get; set;}
		public string fileName {get; set;}
		public string fileOwnerId {get; set;}
		public long fileSizeBytes {get; set;}
		public string fileType {get; set;}
		public string fileNotes {get; set;}
		public DateTime fileUploadedDatetime {get; set;}
    	public DateTime fileExpirationDatetime {get; set;}
    	public bool filePassedAvScan {get; set;}
    	public string fileStatus {get; set;}
    	public bool fileNotifyOnDownload {get; set;}
		public bool downloaded {get; set;}
		public List<User> shareUsers {get; set;}
		
		
		public FLFile ()
		{
			
		}
		
		public FLFile(string fileId, string fileName)
		{
			this.fileId = fileId;
			this.fileName = fileName;
		}
		
		public FLFile(string fileId, string fileName, string fileOwnerId, long fileSizeBytes, string fileType, string fileNotes, DateTime fileUploadedDatetime, DateTime fileExpirationDatetime, bool filePasswdAvScan, string fileStatus, bool fileNotifyOnDownload)
		{
			this.fileId = fileId;
			this.fileName = fileName;
			this.fileOwnerId=fileOwnerId;
			this.fileSizeBytes=fileSizeBytes;
			this.fileType=fileType;
			this.fileNotes=fileNotes;
			this.fileUploadedDatetime=fileUploadedDatetime;
	    	this.fileExpirationDatetime=fileExpirationDatetime;
	    	this.filePassedAvScan=filePassedAvScan;
	    	this.fileStatus=fileStatus;
	    	this.fileNotifyOnDownload=fileNotifyOnDownload;
		}
		
		public override string ToString()
		{
			string fileString = string.Format("This is a healthy file object\n Name: {0}\n ID: {1}\n Owner: {2} \n Passed AV Scan: {3}\n Size (Bytes): {4}", this.fileName,this.fileId,this.fileOwnerId,this.filePassedAvScan, this.fileSizeBytes);
			return fileString;
		}
		public string getFormattedSize()
		{
			string suffix = "B";
			long fileSize = this.fileSizeBytes;
			if (fileSize > 1024)
			{
				suffix = "kB";
				fileSize = fileSize / 1024;
			}
			if (fileSize > 1024)
			{
				suffix = "MB";
				fileSize = fileSize / 1024;
			}
			if (fileSize > 1024)
			{
				suffix = "GB";
				fileSize = fileSize / 1024;
			}
			return string.Format("{0}{1}", fileSize, suffix);
		}
	}
}