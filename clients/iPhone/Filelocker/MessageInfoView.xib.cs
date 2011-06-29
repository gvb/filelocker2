
using System;
using System.Collections.Generic;
using System.Linq;
using MonoTouch.Foundation;
using System.Drawing;
using MonoTouch.UIKit;

namespace Filelocker
{
	public partial class MessageInfoView : UIViewController
	{
		#region Constructors
		FLMessage sourceMessage;
		MessagesViewController controller;

		// The IntPtr and initWithCoder constructors are required for items that need 
		// to be able to be created from a xib rather than from managed code

		public MessageInfoView (IntPtr handle) : base(handle)
		{
			Initialize ();
		}

		[Export("initWithCoder:")]
		public MessageInfoView (NSCoder coder) : base(coder)
		{
			Initialize ();
		}

		public MessageInfoView () : base("MessageInfoView", null)
		{
			Initialize ();
		}
		public MessageInfoView (FLMessage newSourceMessage, MessagesViewController newController) : base("MessageInfoView", null)
		{
			Initialize ();
			this.sourceMessage = newSourceMessage;
			this.controller = newController;
		}

		void Initialize ()
		{
		}
		
		public override void ViewDidLoad() 
		{
			base.ViewDidLoad();
			if (sourceMessage != null)
			{
				btnDelete.Clicked += delegate {
					List<string> messageIds = new List<string>();
					messageIds.Add(sourceMessage.messageId);
					FilelockerConnection.Instance.deleteMessages(messageIds);
					controller.refreshMessageList();
					UIView.BeginAnimations(null,IntPtr.Zero);
					UIView.SetAnimationDuration(1);
					UIView.SetAnimationTransition(UIViewAnimationTransition.CurlUp,NavigationController.View,true);
					NavigationController.PopViewControllerAnimated(false);
					UIView.CommitAnimations();
				};
				txtSender.Text = sourceMessage.messageOwnerId;
				txtBody.Text = sourceMessage.messageBody;
				this.NavigationItem.SetRightBarButtonItem(btnDelete, true);
				this.NavigationItem.Title = sourceMessage.messageSubject;
				try
				{
					FilelockerConnection.Instance.markMessageAsRead(sourceMessage.messageId);
				}
				catch (FilelockerException fe)
				{
					Console.WriteLine("Unable to mark message as read: {0}", fe.Message);
				}
			}
		}
		#endregion
	}
}