using System;
using System.Collections.Generic;
using System.Linq;
using System.IO;
using System.Drawing;
using System.Threading;
using System.Runtime.InteropServices;
using MonoTouch.Foundation;
using MonoTouch.UIKit;
namespace Filelocker
{
	public partial class FilesViewController : UIViewController
	{
		#region Constructors
		
		// The IntPtr and initWithCoder constructors are required for items that need 
		// to be able to be created from a xib rather than from managed code
		public bool initialLoadFinished;
		List<string> validfileIdList;
		List<string> downloadedFileIds;
		List<KeyValuePair<string, List<FLFile>>> fileSectionKVPList;
		public FilesViewController (IntPtr handle) : base(handle)
		{
			Initialize ();
		}

		[Export("initWithCoder:")]
		public FilesViewController (NSCoder coder) : base(coder)
		{
			Initialize ();
		}

		public FilesViewController () : base("FilesViewController", null)
		{
			Initialize ();
		}

		void Initialize ()
		{
		}
		public UIImagePickerController picker;
		public override void ViewDidLoad() 
		{
			validfileIdList = new List<string>();
			base.ViewDidLoad();
			initialLoadFinished = false;
			
			picker = new UIImagePickerController();
			picker.Delegate = new pickerDelegate(this);
			btnRefresh.Clicked += delegate {
				refreshFileList();
			};
			btnUpload.Clicked += delegate {
				var actionSheet = new UIActionSheet("") {"Choose a Photo", "Take a Photo", "Cancel"};
				actionSheet.Style = UIActionSheetStyle.BlackTranslucent;
				actionSheet.ShowInView(View);
				
				actionSheet.Clicked += delegate(object sender, UIButtonEventArgs e) {
					switch(e.ButtonIndex)
					{
					case 0:
						picker.SourceType = UIImagePickerControllerSourceType.PhotoLibrary;
						this.PresentModalViewController(picker, true);
						break;
					case 1:
						try
						{
							picker.SourceType = UIImagePickerControllerSourceType.Camera;
							picker.AllowsEditing = true;
							this.PresentModalViewController(picker, true);
						}
						catch (Exception ex)
						{
							using(var alert = new UIAlertView("Camera Not Available", "The camera is not able to be used on this device.",null, "OK"))
							{
								alert.Show();  
							}
						}
						break;
					case 2:
						break;
					}
				};
			};
		}

		public override void ViewWillAppear (bool animated)
		{
			base.ViewWillAppear (animated);
			if (FilelockerConnection.Instance.connected)
			{
				refreshFileList();
				if (!initialLoadFinished)
				{
					initialLoadFinished = true;
				}
			}
		}
		
		public void refreshFileList()
		{
			if (initialLoadFinished)
			{
				((AppDelegate) UIApplication.SharedApplication.Delegate).Loading(true);
			}
			string docsPath = Environment.GetFolderPath(Environment.SpecialFolder.Personal);
			downloadedFileIds = new List<string>();
			foreach (string filePath in System.IO.Directory.GetFiles(docsPath).ToList())
			{
				string fileName = System.IO.Path.GetFileName(filePath);
				try
				{
					string fileExtension = System.IO.Path.GetExtension(fileName);
					string fileId = fileName.Replace(fileExtension, "");
					downloadedFileIds.Add(fileId);
				}
				catch (Exception e)
				{
					Console.WriteLine("Filename {0} failed to remove extension: {1}", fileName, e.Message);
				}
			}
			Console.WriteLine("Getting files");
			try
			{
				fileSectionKVPList = FilelockerConnection.Instance.populatFileList(downloadedFileIds);
				tblFiles.Source = new DataSource(this);
				tblFiles.ReloadData();
				var validFileIds = from flFile in fileSectionKVPList.SelectMany(i=>i.Value) select flFile.fileId;
				validfileIdList = validFileIds.ToList();
				var cleanupThread = new Thread(CleanupFiles as ThreadStart); 
				cleanupThread.Start();
			}
			catch (FilelockerException fle)
			{
				((AppDelegate) UIApplication.SharedApplication.Delegate).alert("Failed to Refresh Files", fle.Message);
			}
			finally
			{
				if (initialLoadFinished)
				{
					((AppDelegate) UIApplication.SharedApplication.Delegate).Loading(false);
				}
			}
		}
		
		[Export("CleanupFiles")]
		public void CleanupFiles()
		{
			using(var pool = new NSAutoreleasePool())
			{
				string filePath="";
				foreach (string fileId in downloadedFileIds)
				{
					if (!validfileIdList.Contains(fileId) && !fileId.Contains("known_servers"))
					{
						filePath = ((AppDelegate)UIApplication.SharedApplication.Delegate).getFilePathByFileId(fileId);
						Console.WriteLine("Deleting {0}", filePath);
						System.IO.File.Delete(filePath);
					}
				}
			}
		}
		
		private class pickerDelegate : UIImagePickerControllerDelegate
		{
			FilesViewController controller;
			
			public pickerDelegate(FilesViewController newController):base()
			{
				this.controller = newController;
			}
			
			public override void FinishedPickingImage (UIImagePickerController picker, UIImage image, NSDictionary editingInfo)
			{
				try
				{
					string fileName = string.Format("iPhoneImage[{0}].png", DateTime.Now.ToLongTimeString());
					NSData imageData = image.AsPNG();
					imageData.Cast<Byte>();
					byte[] imageBytes = new byte[imageData.Length];
					int length = (int)imageData.Length;
					Marshal.Copy(imageData.Bytes, imageBytes, 0, length);
					((AppDelegate) UIApplication.SharedApplication.Delegate).Loading(true);
					FilelockerConnection.Instance.upload(imageBytes, fileName, "Uploaded via Filelocker for iPhone");
					((AppDelegate) UIApplication.SharedApplication.Delegate).Loading(false);
					controller.refreshFileList();
					picker.DismissModalViewControllerAnimated(true);
				}
				catch (Exception e)
				{
					((AppDelegate) UIApplication.SharedApplication.Delegate).alert("Failed to upload", e.Message);
				}
			}
		}
		
		class DataSource : UITableViewSource
		{
			FilesViewController controller;
 			public DataSource (FilesViewController controller)
			{
				this.controller = controller;
			}
			
			public override int NumberOfSections(UITableView tableView)
			{
				return controller.fileSectionKVPList.Count;
			}
			
			public override string TitleForHeader (UITableView tableView, int section)
			{
				return controller.fileSectionKVPList[section].Key;
			}
			
			public override int RowsInSection(UITableView tableview, int section)
			{
				return controller.fileSectionKVPList[section].Value.Count;
			}
			
			public override UITableViewCell GetCell (UITableView tableView, MonoTouch.Foundation.NSIndexPath indexPath)
			{
				string cellidentifier = "Cell";
				var cell = tableView.DequeueReusableCell(cellidentifier);
				if (cell == null)
				{
					cell = new UITableViewCell(UITableViewCellStyle.Default, cellidentifier);
				}
				//indexPath.Section
				FLFile rowFile = controller.fileSectionKVPList[indexPath.Section].Value[indexPath.Row];
				cell = new FileCell(rowFile, FilelockerConnection.Instance.USERID);
				
				return cell;
			} 
			
			public override void RowSelected (UITableView tableView, MonoTouch.Foundation.NSIndexPath indexPath)
			{
				FLFile rowFile = controller.fileSectionKVPList[indexPath.Section].Value[indexPath.Row];
				FileInfoView fivc = new FileInfoView(rowFile, controller);
				controller.NavigationController.PushViewController(fivc, true);
			}
			
			public override void CommitEditingStyle(UITableView tableView, UITableViewCellEditingStyle editingStyle, NSIndexPath indexPath)
			{
				if (editingStyle == UITableViewCellEditingStyle.Delete)
				{
					FLFile editFile = controller.fileSectionKVPList[indexPath.Section].Value[indexPath.Row];
					try
					{
						FilelockerConnection.Instance.deleteFile(editFile.fileId);
						controller.fileSectionKVPList[indexPath.Section].Value.Remove(editFile);
						tableView.DeleteRows(new [] {indexPath}, UITableViewRowAnimation.Fade);
					}
					catch (FilelockerException fe)
					{
						((AppDelegate) UIApplication.SharedApplication.Delegate).alert("Error Deleting File", fe.Message);
					}
				}
			}
		}

		
		public partial class FileCell : UITableViewCell
		{
			public static Dictionary<string, string> FILE_ICONS_BY_EXTENSION = new Dictionary<string, string>()
			{
				{"log", "Images/application_xp_terminal.png"},
				{"txt", "Images/page_white_text.png"},
				{"pdf", "Images/page_white_acrobat.png"},
				{"default", "Images/page_green.png"}
			};
	
			public FileCell (FLFile sourceFile, string currentUserId) : base(UITableViewCellStyle.Subtitle, "FileCell")
			{
				string[] nameArray = sourceFile.fileName.Split('.');
				string imagePath = "";
				string extension = nameArray[nameArray.Length-1];
				string details = "";
				if (sourceFile.fileOwnerId == currentUserId)
				{
					details+=string.Format("Owner: {0} ", sourceFile.fileOwnerId);
				}
				details += sourceFile.getFormattedSize();
				if (!FILE_ICONS_BY_EXTENSION.TryGetValue(extension, out imagePath))
				{
					imagePath = FILE_ICONS_BY_EXTENSION["default"];
				}
				this.TextLabel.Text = sourceFile.fileName;
				this.DetailTextLabel.Text = details;
				this.ImageView.Image = UIImage.FromFile(imagePath);
				this.TextLabel.TextColor = UIColor.DarkGray;
				if (sourceFile.downloaded)
				{
					this.TextLabel.TextColor = UIColor.Black;
					UIImage downloadedImage = new UIImage("Images/tick.png");
					UIImageView diView = new UIImageView(downloadedImage);
					this.AccessoryView = diView;
				}
			}
		}
		#endregion
	}
}

