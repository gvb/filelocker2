using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.IO;
using MonoTouch.Foundation;
using MonoTouch.UIKit;
using System.Drawing;

namespace Filelocker
{
	public partial class FileInfoView : UIViewController
	{
		#region Constructors
		FLFile sourceFile;
		UIProgressView fileProgress;
		// The IntPtr and initWithCoder constructors are required for items that need 
		// to be able to be created from a xib rather than from managed code

		public FileInfoView (IntPtr handle) : base(handle)
		{
			Initialize ();
			sourceFile = null;
		}

		[Export("initWithCoder:")]
		public FileInfoView (NSCoder coder) : base(coder)
		{
			Initialize ();
			sourceFile = null;
		}

		public FileInfoView () : base("FileInfoView", null)
		{
			Initialize ();
			sourceFile = null;
		}
		
		public FileInfoView (FLFile newSourceFile) : base("FileInfoView", null)
		{
			Initialize ();
			this.sourceFile = newSourceFile;
		}

		void Initialize ()
		{
		}
		public override void ViewDidLoad() 
		{
			base.ViewDidLoad();
			if (sourceFile != null)
			{
				if (FilelockerConnection.Instance.USERID != sourceFile.fileOwnerId)
				{
					btnDelete.Clicked += delegate {
						FilelockerConnection.Instance.hideShare(sourceFile.fileId);
					};
				}
				else
				{
					btnDelete.Clicked += delegate {
						string filePath = ((AppDelegate)UIApplication.SharedApplication.Delegate).GetFilePathByFileId(sourceFile.fileId);
						if (!string.IsNullOrEmpty(filePath))
						{
							try
							{
								System.IO.File.Delete(filePath);
							}
							catch (DirectoryNotFoundException){} //If not found, there's no file to delete
							catch (IOException ioe)
							{
								Console.WriteLine("IO Exception: {0}", ioe.Message);
								((AppDelegate)UIApplication.SharedApplication.Delegate).alert("Unable to delete file", "The file you are trying to delete is currently in use.");
							}
							catch (UnauthorizedAccessException uae)
							{
								Console.WriteLine("Unauthorized Exception: {0}", uae.Message);
								((AppDelegate)UIApplication.SharedApplication.Delegate).alert("Unable to delete file", "Access Denied.");
							}
							
						}
						FilelockerConnection.Instance.deleteFile(sourceFile.fileId);
						UIView.BeginAnimations(null,IntPtr.Zero);
						UIView.SetAnimationDuration(1);
						UIView.SetAnimationTransition(UIViewAnimationTransition.CurlUp,NavigationController.View,true);
						NavigationController.PopViewControllerAnimated(false);
						UIView.CommitAnimations();
					};
				}
				FileInfoViewDataSource dSource = new FileInfoViewDataSource(sourceFile);
				dSource.ButtonRowSelected += delegate(object sender, RowSelectedEventArgs args)
				{
					if (sourceFile.downloaded)
					{
						string strFilePath = "";
						string[] filePathsArray = System.IO.Directory.GetFiles(ApplicationState.FILES_PATH);
						List<string> filePaths = new List<string>(filePathsArray);
						foreach (string filePath in filePaths)
						{
							string fileName = System.IO.Path.GetFileName(filePath);
							try
							{
								string fileExtension = System.IO.Path.GetExtension(fileName);
								string fileId = fileName.Replace(fileExtension, "");
								if (fileId == sourceFile.fileId)
								{
									strFilePath = filePath;
									break;
								}
							}
							catch (Exception e)
							{
								Console.WriteLine("Filename {0} failed to remove extension: {1}", fileName, e.Message);
							}
						}
						this.PresentModalViewController(new FileViewer(strFilePath, sourceFile.fileName), true);
					}
					
				};
				tblFileInfo.Source = dSource;
				this.NavigationItem.SetRightBarButtonItem(btnDelete, true);
				this.NavigationItem.Title = sourceFile.fileName;
			}
			
			
		}
		
//		[Export("DownloadFile")]
//		public void DownloadFile(FLFile sourceFile)
//		{
//			using(var pool = new NSAutoreleasePool())
//			{
//				UITableViewCell cell = tableView.CellAt(indexPath);
//				fileProgress = new UIProgressView(new Rectangle(0,0,100, 40));
//				fileProgress.Progress = 0f;
//				UIView progressView = new UIView(controller.fileProgress.Bounds);
//		
//				progressView.AddSubview(controller.fileProgress);
//				cell.AccessoryView = progressView;
//				var downloadThread = new Thread(DownloadFile as ThreadStart);
//				var updaterThread = new Thread(ProgressUpdater as ThreadStart);
//				cell.TextLabel.Text = "Downloading";
//				downloadThread.Start();
//				updaterThread.Start();
//				tableView.DeselectRow(indexPath, true);
//				FilelockerConnection.Instance.downloadFile(sourceFile.fileId);
//				sourceFile.downloaded = true;
//				//TODO: Something to trigger a reload of the data
//				//controller.tblFileInfo.ReloadData();
//			}
//		}
//	
//		[Export("ProgressUpdater")]
//		public void ProgressUpdater(FLFile sourceFile)
//		{
//			using(var pool = new NSAutoreleasePool())
//			{
//				float fileProgress = 0f;
//				while (fileProgress < 1f)
//				{
//					try
//					{
//						fileProgress  = FilelockerConnection.Instance.FILE_DOWNLOADS[sourceFile.fileId];
//					}
//					catch (Exception e)
//					{
//						Console.WriteLine("There was a problem updating the status {0}", e.Message);
//					}
//					InvokeOnMainThread(delegate {
//						//TODO: update progress somehow
//						//controller.fileProgress.Progress = fileProgress;
//					});
//					Thread.Sleep(200);
//				}
//			}
//		}
//		
	}
	#endregion
}