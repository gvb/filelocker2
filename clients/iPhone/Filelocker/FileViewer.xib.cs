
using System;
using System.Collections.Generic;
using System.Linq;
using MonoTouch.Foundation;
using MonoTouch.UIKit;

namespace Filelocker
{
	public partial class FileViewer : UIViewController
	{
		#region Constructors

		// The IntPtr and initWithCoder constructors are required for items that need 
		// to be able to be created from a xib rather than from managed code
		NSUrlRequest fileRequest;
		string fileName;
		string filePath;
		public FileViewer (IntPtr handle) : base(handle)
		{
			Initialize ();
		}

		[Export("initWithCoder:")]
		public FileViewer (NSCoder coder) : base(coder)
		{
			Initialize ();
		}

		public FileViewer () : base("FileViewer", null)
		{
			Initialize ();
		}
		
		public FileViewer (string filePath, string fileName) : base("FileViewer", null)
		{
			Initialize ();
			this.fileName = fileName;
			this.filePath = filePath;
		}

		void Initialize ()
		{
		}
		
		public override void ViewDidLoad ()
		{
			base.ViewDidLoad ();
			NSUrl fileURL = NSUrl.FromFilename(filePath);
			Console.WriteLine("Filepath: {0}", filePath);
			NSUrlRequest fileRequest = new NSUrlRequest(fileURL);
			webView.LoadFinished += delegate {
				Console.WriteLine("Opened the file");
			};
			webView.LoadStarted += delegate {
				Console.WriteLine("Started loading the fail");
			};
			btnClose.Clicked += delegate {
				this.DismissModalViewControllerAnimated(true);
			};
			nvTitle.Title = fileName;
			Console.WriteLine("Loading request {0}", fileRequest.Url.ToString());
			webView.LoadRequest(fileRequest);
		}
		#endregion
	}
}

