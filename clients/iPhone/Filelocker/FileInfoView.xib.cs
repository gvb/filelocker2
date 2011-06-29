using System;
using System.Collections.Generic;
using System.Linq;
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
						FilelockerConnection.Instance.deleteFile(sourceFile.fileId);
						controller.refreshFileList();
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
									string docsPath = Environment.GetFolderPath(Environment.SpecialFolder.Personal);
									string strFilePath = "";
									foreach (string filePath in System.IO.Directory.GetFiles(docsPath).ToList())
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
									((AppDelegate) UIApplication.SharedApplication.Delegate).startLoading("Downloading File", "");
									FilelockerConnection.Instance.downloadFile(controller.sourceFile.fileId);
									((AppDelegate) UIApplication.SharedApplication.Delegate).stopLoading();
									controller.tblFileInfo.CellAt(indexPath).TextLabel.Text = "Open";		
									controller.sourceFile.downloaded = true;
									tableView.DeselectRow(indexPath, true);
								}
								controller.controller.refreshFileList();
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
			
		}
		#endregion
	}
}