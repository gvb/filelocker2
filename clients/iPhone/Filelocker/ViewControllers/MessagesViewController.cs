using System;
using System.Collections.Generic;
using System.Linq;
using MonoTouch.Foundation;
using MonoTouch.UIKit;
namespace Filelocker
{
	public partial class MessagesViewController : UIViewController
	{
		public MessagesViewController (IntPtr handle) : base(handle)
		{
			Initialize ();
		}

		[Export("initWithCoder:")]
		public MessagesViewController (NSCoder coder) : base(coder)
		{
			Initialize ();
		}

		public MessagesViewController () : base("MessagesViewController", null)
		{
			Initialize ();
		}

		void Initialize ()
		{
		}
		
		public override void ViewDidLoad() 
		{
			base.ViewDidLoad();
			btnCompose.Clicked += delegate {
				this.PresentModalViewController(new MessageComposer(), true);
			};
			btnRefresh.Clicked += delegate {
				refreshMessageList();
			};
			
			if (FilelockerConnection.Instance.CONNECTED)
			{
				refreshMessageList();
			}	
		}
		public void refreshMessageList()
		{
			try  
			{
				Dictionary<string, List<FLMessage>> flMessages = FilelockerConnection.Instance.getAllMessages();
				List<FLMessage> sentMessages = flMessages["outbox"];
				List<FLMessage> rcvdMessages = flMessages["inbox"];
				tblMessages.Source = new DataSource(this, rcvdMessages, sentMessages);
				tblMessages.ReloadData();
			}
			catch (FilelockerException fe)
			{
				using(var alert = new UIAlertView("Message load failure", "Unable to pull messages from Filelocker server: "+fe.Message,null, "OK"))
				{
				    alert.Show();  
				}
			}
		}
		public override void ViewWillAppear(bool animated)
		{
			if (FilelockerConnection.Instance.CONNECTED)
			{
				refreshMessageList();
			}
		}
		
		class DataSource : UITableViewSource
		{
			MessagesViewController controller;
			List<FLMessage> rcvdMessages;
			List<FLMessage> sentMessages;
 			public DataSource (MessagesViewController controller, List<FLMessage> rcvdMessages, List<FLMessage> sentMessages)
			{
				this.controller = controller;
				this.rcvdMessages = rcvdMessages;
				this.sentMessages = sentMessages;
			}
			
			public override int NumberOfSections(UITableView tableView)
			{
				//Keys is equivalent to the number of sections
				return 1;
			}
			
			public override int RowsInSection(UITableView tableview, int section)
			{
				int rowCount = rcvdMessages.Count;
				return rowCount;
			}
			
			public override UITableViewCell GetCell (UITableView tableView, MonoTouch.Foundation.NSIndexPath indexPath)
			{
				string cellidentifier = "Cell";
				var cell = tableView.DequeueReusableCell(cellidentifier);
				if (cell == null)
				{
					cell = new UITableViewCell(UITableViewCellStyle.Default, cellidentifier);
				}
				FLMessage rowMessage = rcvdMessages[indexPath.Row];
				cell = new MessageCell(rowMessage, FilelockerConnection.Instance.USERID);
				
				return cell;
			}
			
			public override void RowSelected (UITableView tableView, MonoTouch.Foundation.NSIndexPath indexPath)
			{
				FLMessage rowMessage = rcvdMessages[indexPath.Row];
				MessageInfoView mivc = new MessageInfoView(rowMessage, this.controller);
				controller.NavigationController.PushViewController(mivc, true);
			}
			
			public override void CommitEditingStyle(UITableView tableView, UITableViewCellEditingStyle editingStyle, NSIndexPath indexPath)
			{
				if (editingStyle == UITableViewCellEditingStyle.Delete)
				{
					FLMessage rowMessage = rcvdMessages[indexPath.Row];
					string messageId = rowMessage.messageId;
					try
					{
						List<string> messageIds = new List<string>();
						messageIds.Add(messageId);
						FilelockerConnection.Instance.deleteMessages(messageIds);
						tableView.DeleteRows(new [] {indexPath}, UITableViewRowAnimation.Fade);
					}
					catch (FilelockerException fe)
					{
						using(var alert = new UIAlertView("Error Message File", fe.Message,null, "OK", null))
						{
						    alert.Show();  
						}
					}
				}
			}
		}

		public partial class MessageCell : UITableViewCell
		{
			public static Dictionary<string, string> MESSAGE_ICONS = new Dictionary<string, string>()
			{
				{"read", "Images/email_open.png"},
				{"new", "Images/email.png"},
				{"sent", "Images/email_go.png"},
				{"default", "Images/email.png"}
			};
	
			public MessageCell (FLMessage sourceMessage, string currentUserId) : base(UITableViewCellStyle.Subtitle, "MessageCell")
			{
				string imagePath = "";				
				if (sourceMessage.messageOwnerId == currentUserId)
				{
					imagePath = MESSAGE_ICONS["sent"];
				}
				else if (sourceMessage.messageOwnerId != currentUserId && sourceMessage.messageViewedDatetime.Equals(new DateTime()))
				{
					imagePath = MESSAGE_ICONS["new"];
				}
				else 
				{
					imagePath = MESSAGE_ICONS["default"];
				}
				this.TextLabel.Text = sourceMessage.messageSubject;
				this.DetailTextLabel.Text = sourceMessage.messageBody;
				this.ImageView.Image = UIImage.FromFile(imagePath);
			}
		}
	}
}

