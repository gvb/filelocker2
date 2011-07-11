using System;
using MonoTouch.UIKit;
using MonoTouch.Foundation;
namespace Filelocker
{
	public partial class MessageCell : UITableViewCell
	{
		public MessageCell (FLMessage sourceMessage, string currentUserId) : base(UITableViewCellStyle.Subtitle, "MessageCell")
		{
			string imagePath = "";				
			if (sourceMessage.messageOwnerId == currentUserId)
			{
				imagePath = Constants.MESSAGE_ICONS["sent"];
			}
			else if (sourceMessage.messageOwnerId != currentUserId && sourceMessage.messageViewedDatetime.Equals(new DateTime()))
			{
				imagePath = Constants.MESSAGE_ICONS["new"];
			}
			else 
			{
				imagePath = Constants.MESSAGE_ICONS["default"];
			}
			this.TextLabel.Text = sourceMessage.messageSubject;
			this.DetailTextLabel.Text = sourceMessage.messageBody;
			this.ImageView.Image = UIImage.FromFile(imagePath);
		}
	}
}