
using System;
using System.Collections.Generic;
using System.Linq;
using System.Drawing;
using MonoTouch.Foundation;
using MonoTouch.UIKit;

namespace Filelocker
{
	public partial class FileShare : UIViewController
	{
		#region Constructors
		public FLFile shareFile;
		// The IntPtr and initWithCoder constructors are required for items that need 
		// to be able to be created from a xib rather than from managed code

		public FileShare (IntPtr handle) : base(handle)
		{
			Initialize ();
		}

		[Export("initWithCoder:")]
		public FileShare (NSCoder coder) : base(coder)
		{
			Initialize ();
		}

		public FileShare (FLFile shareFile) : base("FileShare", null)
		{
			Initialize ();
			this.shareFile = shareFile;
		}

		void Initialize ()
		{
		}
		
		public override void ViewDidLoad ()
		{
			base.ViewDidLoad ();
			btnClose.Clicked += delegate 
			{
				this.DismissModalViewControllerAnimated(true);
			};
			tblShare.Source = new DataSource(this);
		}
		#endregion
		private class ShareUserEntryFieldDelegate : UITextFieldDelegate
		{			
			public ShareUserEntryFieldDelegate ()
			{
			}
			
			public override bool ShouldReturn (UITextField textField)
			{
				textField.ResignFirstResponder();
				return true;
			}
		}
		class DataSource : UITableViewSource
		{
			FileShare controller;
			private ShareUserEntryFieldDelegate entryDelegate;
			public UITextField TargetEntry { get; private set; }
 			public DataSource (FileShare controller)
			{
				this.controller = controller;
				ShareUserEntryFieldDelegate entryDelegate = new ShareUserEntryFieldDelegate();
				TargetEntry = new UITextField (new RectangleF (0, 0, 170f, 30f)) {
							BorderStyle = UITextBorderStyle.None,
							Text = "",
							Delegate = entryDelegate,
							VerticalAlignment = UIControlContentVerticalAlignment.Center,
							AutocapitalizationType = UITextAutocapitalizationType.None,
							AutocorrectionType = UITextAutocorrectionType.No,
							ClearButtonMode = UITextFieldViewMode.WhileEditing,
							ReturnKeyType = UIReturnKeyType.Default,
							KeyboardType = UIKeyboardType.EmailAddress
						};
			}
			
			public override int NumberOfSections(UITableView tableView)
			{
				return 3;
			}
			
			public override string TitleForHeader (UITableView tableView, int section)
			{
				string title="";
				switch(section)
				{
				case 0:
					title = "Share File with User";
					break;
				case 1:
					title = "Share with Groups";
					break;
				case 2:
					title = "Currently Shared With";
					break;
				}
				return title;
			}
			
			public override int RowsInSection(UITableView tableview, int section)
			{
				if (section == 0)
				{
					return 2;
				}
				else if (section == 1)
				{
					return FilelockerConnection.Instance.USER_GROUPS.Count;
				}
				else if (section == 2)
				{
					return controller.shareFile.shareUsers.Count();
				}
				else
				{
					return 0;
				}
			}
			
			public override UITableViewCell GetCell (UITableView tableView, MonoTouch.Foundation.NSIndexPath indexPath)
			{
				string cellidentifier = "Cell";
				var cell = tableView.DequeueReusableCell(cellidentifier);
				if (cell == null)
				{
					cell = new UITableViewCell(UITableViewCellStyle.Default, cellidentifier);
				}
				switch (indexPath.Section)
				{
					case 0:
						switch(indexPath.Row)
						{
							case 0:
								cell.TextLabel.Text = "User ID:";
								cell.AccessoryView = TargetEntry;
								break;
							case 1:
								cell.TextLabel.Text = "Share with User";
								cell.TextLabel.TextAlignment = UITextAlignment.Center;
								cell.TextLabel.TextColor = UIColor.White;
								//cell.TextLabel.BackgroundColor = UIColor.Blue;
								//cell.ContentView.BackgroundColor = UIColor.Blue;
								cell.BackgroundColor = UIColor.Blue;
								break;
						}
						break;
					case 1:
						Group rowGroup = FilelockerConnection.Instance.USER_GROUPS[indexPath.Row];
						cell = new GroupCell(rowGroup, controller.shareFile.fileId);
						break;
					case 2:
						cell = new UserCell(controller.shareFile.shareUsers[indexPath.Row], controller.shareFile.fileId);
						break;
						
				}
				return cell;
			} 
			
			public override void RowSelected (UITableView tableView, MonoTouch.Foundation.NSIndexPath indexPath)
			{
				if (indexPath.Section == 0 && indexPath.Row==1)
				{
					try
					{
						List<string> fileIds = new List<string> {controller.shareFile.fileId};
						string userId = TargetEntry.Text;
						User shareUser = FilelockerConnection.Instance.shareFilesWithUser(fileIds, userId);
						controller.shareFile.shareUsers.Add(shareUser);
						controller.tblShare.ReloadData();
					}
					catch (FilelockerException fle)
					{
						((AppDelegate) UIApplication.SharedApplication.Delegate).alert("Couldn't share file", fle.Message);
					}
				}
				else
				{
					tableView.CellAt(indexPath).ResignFirstResponder();
				}
			}
			
			public override void CommitEditingStyle(UITableView tableView, UITableViewCellEditingStyle editingStyle, NSIndexPath indexPath)
			{
				if (editingStyle == UITableViewCellEditingStyle.Delete)
				{
					if (indexPath.Section == 2)
					{
						User shareUser = controller.shareFile.shareUsers[indexPath.Row];
						try
						{
							List<string> fileIds = new List<string> {controller.shareFile.fileId};
							FilelockerConnection.Instance.unshareFilesWithUser(fileIds, shareUser.userId);
							controller.shareFile.shareUsers.RemoveAt(indexPath.Row);
							tableView.DeleteRows(new [] {indexPath}, UITableViewRowAnimation.Fade);
						}
						catch (FilelockerException fle)
						{
							((AppDelegate) UIApplication.SharedApplication.Delegate).alert("Couldn't un-share file", fle.Message);
						}
					}
				}
			}
		}	
		
		public partial class GroupCell : UITableViewCell
		{
			public GroupCell (Group sourceGroup, string shareFileId) : base(UITableViewCellStyle.Subtitle, "GroupCell")
			{
				string imagePath = "";
				string details = sourceGroup.groupMembers.Count.ToString();
				details += sourceGroup.groupMembers.Count == 0 ? " member" : " members";
				imagePath = "Images/group_add.png";
				this.TextLabel.Text = sourceGroup.groupName;
				this.DetailTextLabel.Text = details;
				this.ImageView.Image = UIImage.FromFile(imagePath);
				GroupShareButton shareButton = new GroupShareButton(new RectangleF (0, 15, 120, 30), sourceGroup, shareFileId);
				Console.WriteLine("Did I find it in the list? {0}", string.Join(",", sourceGroup.filesSharedWithGroup));
				shareButton.SetShared(sourceGroup.filesSharedWithGroup.Contains(shareFileId) ? true : false);
				AccessoryView = shareButton;
				
			}
		}
		
		public partial class UserCell : UITableViewCell
		{
			public UserCell (User shareUser, string shareFileId) : base(UITableViewCellStyle.Subtitle, "UserCell")
			{
				string imagePath = "";
				imagePath = "Images/user_gray.png";
				this.TextLabel.Text = shareUser.userDisplayName;
				this.DetailTextLabel.Text = shareUser.userId;
				this.ImageView.Image = UIImage.FromFile(imagePath);
			}
		}
		
		public class UserShareButton : UIButton
		{
			private string shareFileId;
			public UserShareButton (IntPtr handle) : base(handle)
			{
				Initialize ();
			}
	
			[Export("initWithCoder:")]
			public UserShareButton (NSCoder coder) : base(coder)
			{
				Initialize ();
			}
			
			public UserShareButton (System.Drawing.RectangleF frame) : base (frame)
			{
				Initialize ();
			}
			
			public UserShareButton ()
			{
				Initialize ();
			}
			
			void Initialize ()
			{
				Layer.CornerRadius = 3f;
				Layer.BorderWidth = .3f;
				Layer.BorderColor = UIColor.DarkGray.CGColor;
				Layer.ShadowOffset = new System.Drawing.SizeF (0, -1);
				BackgroundColor = UIColor.Blue;
				SetTitle("Share with User", UIControlState.Normal);
			}
		}
		
		public class GroupShareButton : UIButton
		{
			public bool shared { get; private set; }
			private Group sourceGroup;
			private string shareFileId;
			public GroupShareButton (IntPtr handle) : base(handle)
			{
				Initialize ();
			}
	
			[Export("initWithCoder:")]
			public GroupShareButton (NSCoder coder) : base(coder)
			{
				Initialize ();
			}
			
			public GroupShareButton (System.Drawing.RectangleF frame, Group sGroup, string fileId) : base (frame)
			{
				Initialize ();
				this.sourceGroup = sGroup;
				this.shareFileId = fileId;
			}
			
			public GroupShareButton ()
			{
				Initialize ();
			}
			
			void Initialize ()
			{
				Layer.CornerRadius = 3f;
				Layer.BorderWidth = .3f;
				Layer.BorderColor = UIColor.DarkGray.CGColor;
				Layer.ShadowOpacity = .9f;
				Layer.ShadowColor = UIColor.DarkGray.CGColor;
				Layer.ShadowOffset = new System.Drawing.SizeF (0, -1);
				shared = false;
				BackgroundColor = UIColor.Green;
				this.TouchUpInside += delegate(object sender, EventArgs e) {
					if (shared)
					{
						unshareFile();
						Console.WriteLine("Setting to false");
					}
					else
					{
						shareFile();
						Console.WriteLine("Setting to true");
					}
				};
			}
			private void shareFile()
			{
				try
				{
					List<string> fileIds = new List<string> { shareFileId };
					FilelockerConnection.Instance.shareFilesWithGroup(fileIds, sourceGroup.groupId);
					SetShared(true);
				}
				catch (FilelockerException fle)
				{
					((AppDelegate) UIApplication.SharedApplication.Delegate).alert("Couldn't share file", fle.Message);
				}
			}
			private void unshareFile()
			{
				try
				{
					List<string> fileIds = new List<string> { shareFileId };
					FilelockerConnection.Instance.unshareFilesWithGroup(fileIds, sourceGroup.groupId);
					SetShared(false);
				}
				catch (FilelockerException fle)
				{
					((AppDelegate) UIApplication.SharedApplication.Delegate).alert("Couldn't un-share file", fle.Message);
				}
			}
			public void SetShared (bool isShared)
			{
				if (isShared)
				{
					BackgroundColor = UIColor.Red;
					SetTitle ("Unshare", UIControlState.Normal);
					shared = true;
					
				}
				else
				{
					BackgroundColor = UIColor.Green;
					SetTitle ("Share", UIControlState.Normal);
					shared=false;
				}
			}
		}
		
	}
}

