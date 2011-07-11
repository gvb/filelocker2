using System;
using MonoTouch.UIKit;

namespace Filelocker
{
	public partial class FileCell : UITableViewCell
	{
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
			if (!Constants.FILE_ICONS_BY_EXTENSION.TryGetValue(extension, out imagePath))
			{
				imagePath = Constants.FILE_ICONS_BY_EXTENSION["default"];
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
}

