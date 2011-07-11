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
			picker.Delegate = new PickerDelegate(this);
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
			foreach (string filePath in System.IO.Directory.GetFiles(ApplicationState.FILES_PATH).ToList())
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
			fileSectionKVPList = FilelockerConnection.Instance.PopulateFileList(downloadedFileIds, true);
			BuildFileList();
			if (FilelockerConnection.Instance.CONNECTED)
			{
				Console.WriteLine("File refresh started for network load");
				StartFileRefresh();
			}
		}
		public void StartFileRefresh()
		{
			refreshThread = new Thread(RefreshFiles as ThreadStart);
			UIApplication.SharedApplication.NetworkActivityIndicatorVisible = true;
			refreshThread.Start();
		}
		public void BuildFileList()
		{
			try
			{
				tblFiles.Source = new FilesDataSource(this.NavigationController, fileSectionKVPList);
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
						filePath = ((AppDelegate)UIApplication.SharedApplication.Delegate).GetFilePathByFileId(fileId);
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
						fileSectionKVPList = FilelockerConnection.Instance.PopulateFileList(downloadedFileIds, false);
						InvokeOnMainThread(delegate {
							Console.WriteLine("File refresh ended, rebuilding table");
							BuildFileList();	
							UIApplication.SharedApplication.NetworkActivityIndicatorVisible = false;
						});
					}
					catch (FilelockerException fle)
					{
						Console.WriteLine("derp {0}", fle.Message);
					}
				}
			}
			catch (ThreadAbortException)
			{
				Console.WriteLine("Aborting RefreshFiles");
				UIApplication.SharedApplication.NetworkActivityIndicatorVisible = false;
			}
			
		}
		
		private class PickerDelegate : UIImagePickerControllerDelegate
		{
			FilesViewController controller;
			
			public PickerDelegate(FilesViewController newController):base()
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
					controller.StartFileRefresh();
					picker.DismissModalViewControllerAnimated(true);
				}
				catch (Exception e)
				{
					((AppDelegate) UIApplication.SharedApplication.Delegate).alert("Failed to upload", e.Message);
				}
			}
		}
		#endregion
	}
}

