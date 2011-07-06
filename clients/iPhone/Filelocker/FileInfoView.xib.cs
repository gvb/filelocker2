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
		FilesViewController controller;
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
		
		public FileInfoView (FLFile newSourceFile, FilesViewController fvc) : base("FileInfoView", null)
		{
			Initialize ();
			this.sourceFile = newSourceFile;
			this.controller = fvc;
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
						string filePath = ((AppDelegate)UIApplication.SharedApplication.Delegate).getFilePathByFileId(sourceFile.fileId);
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
						controller.startFileRefresh();
						UIView.BeginAnimations(null,IntPtr.Zero);
						UIView.SetAnimationDuration(1);
						UIView.SetAnimationTransition(UIViewAnimationTransition.CurlUp,NavigationController.View,true);
						NavigationController.PopViewControllerAnimated(false);
						UIView.CommitAnimations();
					};
				}
				tblFileInfo.Source = new DataSource(this);
				this.NavigationItem.SetRightBarButtonItem(btnDelete, true);
				this.NavigationItem.Title = sourceFile.fileName;
			}
			
			
		}
		
	 	class DataSource : UITableViewSource
		{
			FileInfoView controller;
			UISwitch sw;
 			public DataSource (FileInfoView controller)
			{
				this.controller = controller;
			}
			
			public override int NumberOfSections(UITableView tableView)
			{
				return 2;
			}
			
			public override string TitleForHeader (UITableView tableView, int section)
			{
				string title="";
				switch(section)
				{
					case 0:
						title = "File Information";
						break;
					case 1:
						title = "Actions";
						break;
				}
				return title;
			}
			
			public override int RowsInSection(UITableView tableview, int section)
			{
				if (section == 0)
				{
					return 3;
				}
				else if (section == 1)
				{
					return 2;
				}
				else 
				{
					return 0;
				}
			}
			
			public override UITableViewCell GetCell (UITableView tableView, MonoTouch.Foundation.NSIndexPath indexPath)
			{
				string cellidentifier = "Cell";
				var cell = tableView.DequeueReusableCell(cellidentifier);
				if (cell == null)
				{
					cell = new UITableViewCell(UITableViewCellStyle.Subtitle, cellidentifier);
				}
				switch (indexPath.Section)
				{
					case 0:
						UIFont titleFont = UIFont.FromName ("Helvetica-Bold", 17);
						UIFont detailFont = UIFont.FromName ("Helvetica-Bold", 12);
						switch(indexPath.Row)
						{
							case 0:
								cell.TextLabel.Font = detailFont;				
								cell.DetailTextLabel.Font = titleFont;
								cell.TextLabel.Text = "File Name";
								cell.DetailTextLabel.Text = controller.sourceFile.fileName;
								break;
							case 1:
								cell.TextLabel.Font = detailFont;				
								cell.DetailTextLabel.Font = titleFont;
								cell.TextLabel.Text = "File Size";
								cell.DetailTextLabel.Text = controller.sourceFile.getFormattedSize();
								break;
							case 2:
								cell.TextLabel.Font = detailFont;
								cell.TextLabel.Text = "Download Notifications:";
								sw = new UISwitch (new RectangleF (198f, 12f, 94f, 27f));
								sw.On = controller.sourceFile.fileNotifyOnDownload;
								sw.ValueChanged += delegate {
									try
									{
										Console.WriteLine("Hey, trying");
										FilelockerConnection.Instance.toggleFileNotifications(controller.sourceFile.fileId, sw.On);
									}
									catch (FilelockerException fe)
									{
										((AppDelegate) UIApplication.SharedApplication.Delegate).alert("Failed to Update", fe.Message);    
									}
									catch (Exception e)
									{
										((AppDelegate) UIApplication.SharedApplication.Delegate).alert("Error: ", e.Message);    
									}
								};
								cell.AccessoryView = sw;
								break;
						}
						break;
					case 1:
						cell.TextLabel.Font = UIFont.FromName ("Helvetica-Bold", 20);
						cell.TextLabel.TextAlignment = UITextAlignment.Center;
						switch(indexPath.Row)
						{
							case 0:
								cell.TextLabel.Text = "Share";
								break;
							case 1:
								if (controller.sourceFile.downloaded)
								{
									cell.TextLabel.Text = "Open";
									cell.AccessoryView = null; //Purge progress bar
								}
								else
								{
									cell.TextLabel.Text = "Download";
								}
								break;
						}
						break;
				}
				return cell;
			} 
			
			public override void RowSelected (UITableView tableView, MonoTouch.Foundation.NSIndexPath indexPath)
			{
				switch(indexPath.Section)
				{
					case 0:
						break;
					case 1:
						switch(indexPath.Row)
						{
							case 0:
								controller.PresentModalViewController(new FileShare(controller.sourceFile),true);
								break;
							case 1:
								if (controller.sourceFile.downloaded)
								{
									string strFilePath = "";
									foreach (string filePath in System.IO.Directory.GetFiles(FilelockerConnection.Instance.FILES_PATH).ToList())
									{
										string fileName = System.IO.Path.GetFileName(filePath);
										try
										{
											string fileExtension = System.IO.Path.GetExtension(fileName);
											string fileId = fileName.Replace(fileExtension, "");
											if (fileId == controller.sourceFile.fileId)
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
									controller.PresentModalViewController(new FileViewer(strFilePath, controller.sourceFile.fileName), true);
									tableView.DeselectRow(indexPath, true);
								}
								else
								{
									UITableViewCell cell = controller.tblFileInfo.CellAt(indexPath);
									controller.fileProgress = new UIProgressView(new Rectangle(0,0,100, 40));
									controller.fileProgress.Progress = 0f;
									UIView progressView = new UIView(controller.fileProgress.Bounds);
							
									progressView.AddSubview(controller.fileProgress);
									cell.AccessoryView = progressView;
									var downloadThread = new Thread(DownloadFile as ThreadStart);
									var updaterThread = new Thread(ProgressUpdater as ThreadStart);
									cell.TextLabel.Text = "Downloading";
									downloadThread.Start();
									updaterThread.Start();
									tableView.DeselectRow(indexPath, true);
								}
								controller.controller.startFileRefresh();
								break;
						}
						break;
				}
			}
			
			public override void CommitEditingStyle(UITableView tableView, UITableViewCellEditingStyle editingStyle, NSIndexPath indexPath)
			{
				if (editingStyle == UITableViewCellEditingStyle.Delete)
				{
				}
			}
			
			[Export("DownloadFile")]
			public void DownloadFile()
			{
				using(var pool = new NSAutoreleasePool())
				{
					FilelockerConnection.Instance.downloadFile(controller.sourceFile.fileId);
					controller.sourceFile.downloaded = true;
					controller.tblFileInfo.ReloadData();
				}
			}
			[Export("ProgressUpdater")]
			public void ProgressUpdater()
			{
				using(var pool = new NSAutoreleasePool())
				{
					float fileProgress = 0f;
					while (fileProgress < 1f)
					{
						try
						{
							fileProgress  = FilelockerConnection.Instance.FILE_DOWNLOADS[controller.sourceFile.fileId];
						}
						catch (Exception e)
						{
							Console.WriteLine("There was a problem updating the status {0}", e.Message);
						}
						InvokeOnMainThread(delegate {
							controller.fileProgress.Progress = fileProgress;
						});
						Thread.Sleep(200);
					}
					
				}
			}
			
		}
		#endregion
	}
}