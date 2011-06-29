using System;
using System.Collections.Generic;
using System.Linq;
using System.Drawing;
using MonoTouch.Foundation;
using MonoTouch.UIKit;
namespace Filelocker
{
	public partial class MessageComposerTableViewController : UITableViewController
	{
		public MessageComposerTableViewController (IntPtr handle) : base(handle)
		{
			Initialize ();
		}

		[Export("initWithCoder:")]
		public MessageComposerTableViewController (NSCoder coder) : base(coder)
		{
			Initialize ();
		}

		public MessageComposerTableViewController () : base("MessageComposerTableViewController", null)
		{
			Initialize ();
		}

		void Initialize ()
		{
		}

		
		public override void ViewDidLoad ()
		{
			base.ViewDidLoad ();
			tblMessage.Source = new MessageComposerTableSource(new MessageComposerTableEntryFieldDelegate(this), new MessageComposerTableBodyEntryFieldDelegate(this));
			btnCancel.Clicked += delegate {
				this.DismissModalViewControllerAnimated(true);
			};
			btnSend.Clicked += delegate {
				string recipient = ((MessageComposerTableSource)tblMessage.Source).RecipientEntry.Text;
				string subject = ((MessageComposerTableSource)tblMessage.Source).SubjectEntry.Text;
				string body = ((MessageComposerTableSource)tblMessage.Source).BodyEntry.Text;
			};
		}
		
		private class MessageComposerTableEntryFieldDelegate : UITextFieldDelegate
		{
			MessageComposerTableViewController controller;
			
			public MessageComposerTableEntryFieldDelegate (MessageComposerTableViewController mController)
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
			public MessageComposerTableViewController controller;
			
			public MessageComposerTableBodyEntryFieldDelegate (MessageComposerTableViewController mController)
			{
				controller = mController;
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
					if (BodyEntry.Frame.Height > 360f)
					{
						return BodyEntry.Frame.Height;
					}
					else
					{
						return 360f;
					}
				}
				else
				{
					return 35f;
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
						cell.Frame = BodyEntry.Frame;
						break;
				}
				
				return cell;
			}
			
			private void BuildEntryFields()
			{
				RecipientEntry = new UITextField (new RectangleF (0, 0, 190f, 30f)) {
							BorderStyle = UITextBorderStyle.None,
							Text = NSUserDefaults.StandardUserDefaults.StringForKey("username"),
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
				
				BodyEntry = new UITextView(new RectangleF(0,0,320, 480));
				BodyEntry.BackgroundColor = UIColor.White;
				BodyEntry.Delegate = bodyEntryDelegate;
				BodyEntry.UserInteractionEnabled = true;
				BodyEntry.Changed += delegate {
					bodyEntryDelegate.controller.tblMessage.BeginUpdates();
					bodyEntryDelegate.controller.tblMessage.EndUpdates();
				};
				//PasswordEntry.EditingDidEnd += delegate { Password = PasswordEntry.Text; };
			}			
		}
	}
}

