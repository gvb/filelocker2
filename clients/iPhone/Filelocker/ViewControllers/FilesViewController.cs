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
		List<string> validfileIdList;
		List<string> downloadedFileIds;
		//TODO: Extract cleanup functions, BL as much as possible
		Thread refreshThread;
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
			base.ViewDidLoad();
			validfileIdList = new List<string>();
			picker = new UIImagePickerController();
			picker.Delegate = new pickerDelegate(this);
			btnRefresh.Clicked += delegate {
				if (refreshThread != null)
					refreshThread.Abort();
				refreshThread = new Thread(RefreshFiles as ThreadStart);
				UIApplication.SharedApplication.NetworkActivityIndicatorVisible = true;
				refreshThread.Start();
			};
			btnUpload.Clicked += delegate {
				var actionSheet = new UIActionSheet("") {"Choose a Photo", "Take a Photo", "Cancel"};
				actionSheet.CancelButtonIndex = 2;
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
							Console.WriteLine("Couldn't load camera stuff: {0}", ex.Message);
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
			downloadedFileIds = new List<string>();
			foreach (string filePath in System.IO.Directory.GetFiles(FilelockerConnection.Instance.FILES_PATH).ToList())
			{
				string fileName = System.IO.Path.GetFileName(filePath);
				try
				{
					string fileExtension = System.IO.Path.GetExtension(fileName);
					string fileId = fileName.Replace(fileExtension, "");
					downloadedFileIds.Add(fileId);
					Console.WriteLine("Adding fileId: {0}", fileId);
				}
				catch (Exception e)
				{
					Console.WriteLine("Filename {0} failed to remove extension: {1}", fileName, e.Message);
				}
			}
			fileSectionKVPList = FilelockerConnection.Instance.populateFileList(downloadedFileIds, true);
			buildFileList();
			if (FilelockerConnection.Instance.CONNECTED)
			{
				Console.WriteLine("File refresh started for network load");
				startFileRefresh();
			}
		}
		public void startFileRefresh()
		{
			refreshThread = new Thread(RefreshFiles as ThreadStart);
			UIApplication.SharedApplication.NetworkActivityIndicatorVisible = true;
			refreshThread.Start();
		}
		public void buildFileList()
		{
			try
			{
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
		}
		
		[Export("CleanupFiles")]
		public void CleanupFiles()
		{
			using(var pool = new NSAutoreleasePool())
			{
				string filePath="";
				Console.WriteLine("The valid files are {0}", string.Join(",",validfileIdList));
				Console.WriteLine("The downloaded files are {0}", string.Join(",",downloadedFileIds));
				foreach (string fileId in downloadedFileIds)
				{
					if (!validfileIdList.Contains(fileId))
					{
						filePath = ((AppDelegate)UIApplication.SharedApplication.Delegate).getFilePathByFileId(fileId);
						Console.WriteLine("Deleting {0}", filePath);
						System.IO.File.Delete(filePath);
					}
				}
			}
		}
		
		[Export("RefreshFiles")]
		public void RefreshFiles()
		{
			try{
				using(var pool = new NSAutoreleasePool())
				{
					try
					{
						fileSectionKVPList = FilelockerConnection.Instance.populateFileList(downloadedFileIds, false);
						InvokeOnMainThread(delegate {
							Console.WriteLine("File refresh ended, rebuilding table");
							buildFileList();	
							UIApplication.SharedApplication.NetworkActivityIndicatorVisible = false;
						});
					}
					catch (FilelockerException fle)
					{
						Console.WriteLine("derp {0}", fle.Message);
					}
				}
			}
			catch (ThreadAbortException tae)
			{
				UIApplication.SharedApplication.NetworkActivityIndicatorVisible = false;
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
					FilelockerConnection.Instance.upload(imageBytes, fileName, "Uploaded via Filelocker for iPhone");
					controller.startFileRefresh();
					picker.DismissModalViewControllerAnimated(true);
				}
				catch (Exception e)
				{
					((AppDelegate) UIApplication.SharedApplication.Delegate).alert("Failed to upload", e.Message);
				}
			}
		}
		
		//TODO: Pull out into separate data source classes, as well with FileCell
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
			//TODO: Drop in the constants
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

