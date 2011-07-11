using System;
using System.Collections.Generic;
using MonoTouch.UIKit;
using MonoTouch.Foundation;
namespace Filelocker
{
	class MessagesDataSource : UITableViewSource
	{
		MessagesViewController controller;
		List<FLMessage> rcvdMessages;
		List<FLMessage> sentMessages;
		public MessagesDataSource (MessagesViewController controller, List<FLMessage> rcvdMessages, List<FLMessage> sentMessages)
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
}

