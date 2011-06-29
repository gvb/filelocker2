
using System;
using System.Collections.Generic;
using System.Linq;
using MonoTouch.Foundation;
using MonoTouch.UIKit;
using System.Runtime.InteropServices;
namespace Filelocker
{
	public partial class UploadView : UIViewController
	{
		#region Constructors

		// The IntPtr and initWithCoder constructors are required for items that need 
		// to be able to be created from a xib rather than from managed code

		public UploadView (IntPtr handle) : base(handle)
		{
			Initialize ();
		}

		[Export("initWithCoder:")]
		public UploadView (NSCoder coder) : base(coder)
		{
			Initialize ();
		}

		public UploadView () : base("UploadView", null)
		{
			Initialize ();
		}

		void Initialize ()
		{
		}
		public UIImagePickerController picker;
		public override void ViewDidLoad ()
		{
			base.ViewDidLoad ();
			picker = new UIImagePickerController();
			picker.Delegate = new pickerDelegate(this);
			btnClose.Clicked += delegate {
				this.DismissModalViewControllerAnimated(true);
			};
			btnCamera.Clicked += delegate {
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
		
		private class pickerDelegate : UIImagePickerControllerDelegate
		{
			private UploadView controller;
			
			public pickerDelegate(UploadView newController):base()
			{
				this.controller = newController;
			}
			
			public override void FinishedPickingImage (UIImagePickerController picker, UIImage image, NSDictionary editingInfo)
			{
				controller.imageView.Image = image;
				string fileName = string.Format("iPhoneImage[{0}].png", DateTime.Now.ToLongTimeString());
				NSData imageData = image.AsPNG();
				imageData.Cast<Byte>();
				byte[] imageBytes = new byte[imageData.Length];
				int length = (int)imageData.Length;
				Marshal.Copy(imageData.Bytes, imageBytes, 0, length);
				UIAlertView alert = ((AppDelegate) UIApplication.SharedApplication.Delegate).startLoading("Uploading File", "");
				FilelockerConnection.Instance.upload(imageBytes, fileName, "Uploaded via Filelocker for iPhone");
				((AppDelegate) UIApplication.SharedApplication.Delegate).stopLoading(alert);
				picker.DismissModalViewControllerAnimated(true);
			}
		}
		#endregion
	}
}

