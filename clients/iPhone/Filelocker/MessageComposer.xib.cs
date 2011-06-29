
using System;
using System.Collections.Generic;
using System.Linq;
using System.Drawing;
using MonoTouch.Foundation;
using MonoTouch.UIKit;

namespace Filelocker
{
	public partial class MessageComposer : UIViewController
	{
		#region Constructors

		// The IntPtr and initWithCoder constructors are required for items that need 
		// to be able to be created from a xib rather than from managed code

		string Subject;
		List<string> RecipientIds;
		public MessageComposer (IntPtr handle) : base(handle)
		{
			Initialize ();
		}

		[Export("initWithCoder:")]
		public MessageComposer (NSCoder coder) : base(coder)
		{
			Initialize ();
		}

		public MessageComposer () : base("MessageComposer", null)
		{
			Initialize ();
		}
		
		public MessageComposer(string subject, List<string> recipientIds): base("MessageComposer", null)
		{
			Initialize();
			Subject = subject;
			RecipientIds = recipientIds;
		}
		void Initialize ()
		{
			Subject = "";
			RecipientIds = new List<string>();
		}
		
		#endregion
		public override void ViewDidLoad ()
		{
			base.ViewDidLoad ();
			tblMessage.Source = new MessageComposerTableSource(new MessageComposerTableEntryFieldDelegate(this), new MessageComposerTableBodyEntryFieldDelegate(this));
			((MessageComposerTableSource)tblMessage.Source).SubjectEntry.Text = Subject;
			((MessageComposerTableSource)tblMessage.Source).RecipientEntry.Text = string.Join(",", RecipientIds);
			btnCancel.Clicked += delegate {
				this.DismissModalViewControllerAnimated(true);
			};
			btnSend.Clicked += delegate {
				string recipient = ((MessageComposerTableSource)tblMessage.Source).RecipientEntry.Text;
				List<string> recipientIds = new List<string>();
				foreach (string id in recipient.Split(',',';'))
				{
					recipientIds.Add(id);
				}
				string subject = ((MessageComposerTableSource)tblMessage.Source).SubjectEntry.Text;
				string body = ((MessageComposerTableSource)tblMessage.Source).BodyEntry.Text;
				try
				{
					FilelockerConnection.Instance.sendMessage(recipientIds, subject, body);
					this.DismissModalViewControllerAnimated(true);
				}
				catch (FilelockerException fe)
				{
					using(var alert = new UIAlertView("Failed to Send Message", string.Format("The message was not sent because: {0}", fe.Message),null, "OK"))
					{
					    alert.Show();  
					}
				}
			};
		}
		
		private class MessageComposerTableEntryFieldDelegate : UITextFieldDelegate
		{
			MessageComposer controller;
			
			public MessageComposerTableEntryFieldDelegate (MessageComposer mController)
			{
				controller = mController;
			}
			
			public override bool ShouldReturn (UITextField textField)
			{
				textField.ResignFirstResponder();
				return true;
			}
		}
		
		private class MessageComposerTableBodyEntryFieldDelegate : UITextViewDelegate
		{
			public MessageComposer controller;
			public float lastContentSizeHeight {get; set;}
			
			public MessageComposerTableBodyEntryFieldDelegate (MessageComposer mController)
			{
				controller = mController;
				lastContentSizeHeight = 0f;
			}
		}
		
		private class MessageComposerTableSource : UITableViewSource
		{	
			public UITextField RecipientEntry { get; private set; }
			public UITextField SubjectEntry { get; private set; }
			public UITextView BodyEntry { get; private set; }
			
			private MessageComposerTableEntryFieldDelegate entryDelegate;
			private MessageComposerTableBodyEntryFieldDelegate bodyEntryDelegate;

			public MessageComposerTableSource (MessageComposerTableEntryFieldDelegate entryFieldDelegate, MessageComposerTableBodyEntryFieldDelegate bodyEntryFieldDelegate) : base ()
			{
				entryDelegate = entryFieldDelegate;
				bodyEntryDelegate = bodyEntryFieldDelegate;
				BuildEntryFields();
			}
			
			public override void RowSelected(UITableView tableView, NSIndexPath indexPath) 
			{
				tableView.DeselectRow (indexPath, false);
			}
			
			public override int NumberOfSections(UITableView tableview) 
			{
				return 1;
			}
			
			public override float GetHeightForRow (UITableView tableView, NSIndexPath indexPath)
			{
				if (indexPath.Row == 2)
				{
					float rowHeight = BodyEntry.ContentSize.Height + 216;
					return rowHeight;
				}
				else
				{
					return 30f;
				}
			}
			public override int RowsInSection (UITableView tableview, int section) 
			{
				int rows = 3;
				return rows;
			}
			
			public override UITableViewCell GetCell (UITableView tableView, NSIndexPath indexPath)
		    {	
				string cellId = "cell";
		    	UITableViewCell cell = tableView.DequeueReusableCell(cellId); 
		
		    	if (cell == null )
		    	{	
		    		cell = new UITableViewCell(UITableViewCellStyle.Value1, cellId);
		    	}

				switch (indexPath.Row)
				{
					case 0:
						cell.TextLabel.Text = "Recipient";
						cell.TextLabel.TextColor = UIColor.LightGray;
						cell.AccessoryView = RecipientEntry;
						break;
					case 1:
						cell.TextLabel.Text = "Subject";
						cell.TextLabel.TextColor = UIColor.LightGray;
						cell.AccessoryView = SubjectEntry;
						break;
					case 2:
						cell.ContentView.AddSubview(BodyEntry);
						break;
				}
				return cell;
			}
			
			private void BuildEntryFields()
			{
				RecipientEntry = new UITextField (new RectangleF (0, 0, 190f, 30f)) {
							BorderStyle = UITextBorderStyle.None,
							Text = "",
							Delegate = entryDelegate,
							VerticalAlignment = UIControlContentVerticalAlignment.Center,
							AutocapitalizationType = UITextAutocapitalizationType.None,
							AutocorrectionType = UITextAutocorrectionType.No,
							ClearButtonMode = UITextFieldViewMode.WhileEditing,
							ReturnKeyType = UIReturnKeyType.Next,
							KeyboardType = UIKeyboardType.EmailAddress
						};
				
				//UsernameEntry.EditingDidEnd += delegate { Username = UsernameEntry.Text; };
				
				SubjectEntry = new UITextField(new RectangleF (0, 0, 190f, 30f)) {
							Text = "",
							Delegate = entryDelegate,
							VerticalAlignment = UIControlContentVerticalAlignment.Center,
							AutocapitalizationType = UITextAutocapitalizationType.None,
							AutocorrectionType = UITextAutocorrectionType.No,
							ClearButtonMode = UITextFieldViewMode.WhileEditing,
							ReturnKeyType = UIReturnKeyType.Next,
							KeyboardType = UIKeyboardType.Default
						};
				
				BodyEntry = new UITextView(new RectangleF(0,0,320f, 296f));
				BodyEntry.BackgroundColor = UIColor.White;
				BodyEntry.ScrollEnabled = false;
				BodyEntry.Delegate = bodyEntryDelegate;
				bodyEntryDelegate.lastContentSizeHeight = BodyEntry.ContentSize.Height;
				BodyEntry.UserInteractionEnabled = true;
				BodyEntry.Changed += delegate {
					UITableView tbl = bodyEntryDelegate.controller.tblMessage;
					
					if (BodyEntry.ContentSize.Height > 140)
					{
						if (bodyEntryDelegate.lastContentSizeHeight != BodyEntry.ContentSize.Height)
						{
							BodyEntry.Frame.Height = (BodyEntry.ContentSize.Height - 140)+356;
							tbl.BeginUpdates();
							tbl.EndUpdates();
							tbl.SetContentOffset(new PointF(0,tbl.ContentSize.Height - tbl.Frame.Size.Height), false);
						}
					}
					else
					{
						BodyEntry.Frame.Height = 356;
						tbl.BeginUpdates();
						tbl.EndUpdates();
					}					
					
					//BodyEntry.ScrollRangeToVisible(new NSRange(BodyEntry.Text.Length -1, 1));
				};
				//PasswordEntry.EditingDidEnd += delegate { Password = PasswordEntry.Text; };
			}	
			
			
		}
	}
}

