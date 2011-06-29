
using System;
using System.IO;
using System.Collections.Generic;
using System.Linq;
using MonoTouch.Foundation;
using MonoTouch.UIKit;

namespace Filelocker
{
	public partial class DownloadScreen : UIViewController
	{
		#region Constructors

		// The IntPtr and initWithCoder constructors are required for items that need 
		// to be able to be created from a xib rather than from managed code

		public DownloadScreen (IntPtr handle) : base(handle)
		{
			Initialize ();
		}

		[Export("initWithCoder:")]
		public DownloadScreen (NSCoder coder) : base(coder)
		{
			Initialize ();
		}

		public DownloadScreen () : base("DownloadScreen", null)
		{
			Initialize ();
		}

		void Initialize ()
		{
		}
		
		public override void ViewDidLoad() 
		{
			base.ViewDidLoad();
			btnDownload.TouchUpInside += delegate {
				FilelockerConnection.Instance.DownloadFile(txtFileId.Text);
			};
		}
		
		#endregion
	}
}

