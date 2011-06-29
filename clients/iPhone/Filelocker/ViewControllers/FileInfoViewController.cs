using System;
using MonoTouch.UIKit;
using MonoTouch.Foundation;
namespace Filelocker
{
	public partial class FileInfoViewController : UIViewController
	{
		private FLFile sourceFile;
		public FileInfoViewController (IntPtr handle) : base(handle)
		{
			Initialize ();
		}

		[Export("initWithCoder:")]
		public FileInfoViewController (NSCoder coder) : base(coder)
		{
			Initialize ();
		}

		public FileInfoViewController () : base("FileInfoViewController", null)
		{
			Initialize ();
		}
		
		public FileInfoViewController (FLFile newSourceFile) : base("FileInfoViewController", null)
		{
			this.sourceFile = newSourceFile;
			Initialize ();
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
					btnDelete.TitleLabel.Text = "Hide Shared File";
					btnDelete.TouchUpInside += delegate {
						FilelockerConnection.Instance.hideShare(sourceFile.fileId);
					};
				}
				else
				{
					btnDelete.TouchUpInside += delegate {
						FilelockerConnection.Instance.deleteFile(sourceFile.fileId);
					};
				}
				lblFileId.Text = sourceFile.fileId;
				lblFileName.Text = sourceFile.fileName;
				lblFileSize.Text = sourceFile.getFormattedSize();
				lblFileExpiration.Text = sourceFile.fileExpirationDatetime.ToShortDateString();
			}
		}
		
	}
}

