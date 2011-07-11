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
				tblMessages.Source = new MessagesDataSource(this, rcvdMessages, sentMessages);
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
	}
}