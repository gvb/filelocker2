using System;
using System.Collections.Generic;
using System.Linq;
using MonoTouch.Foundation;
using MonoTouch.UIKit;
namespace Filelocker
{
	public class UserSearchController : UIViewController
	{
		#region Constructors
		
		// The IntPtr and initWithCoder constructors are required for items that need 
		// to be able to be created from a xib rather than from managed code
		public UserSearchController (IntPtr handle) : base(handle)
		{
			Initialize ();
		}

		[Export("initWithCoder:")]
		public UserSearchController (NSCoder coder) : base(coder)
		{
			Initialize ();
		}

		public UserSearchController () : base("UserSearchController", null)
		{
			Initialize ();
		}

		void Initialize ()
		{
		}

		public override void ViewDidLoad() 
		{
			base.ViewDidLoad();
		}
		
		class DataSource : UITableViewSource
		{
			UserSearchController controller;
 			public DataSource (UserSearchController controller)
			{
				this.controller = controller;
			}
			
			public override int NumberOfSections(UITableView tableView)
			{
				//Keys is equivalent to the number of sections
				return 1;
			}
			
			public override string TitleForHeader (UITableView tableView, int section)
			{
				string sectionTitle = "Title";
				return sectionTitle;
			}
			
			public override int RowsInSection(UITableView tableview, int section)
			{
				return 1;
			}
			
			public override UITableViewCell GetCell (UITableView tableView, MonoTouch.Foundation.NSIndexPath indexPath)
			{
				string cellidentifier = "Cell";
				var cell = tableView.DequeueReusableCell(cellidentifier);
				if (cell == null)
				{
					cell = new UITableViewCell(UITableViewCellStyle.Default, cellidentifier);
				}
				//indexPath.Section
				User rowUser = new User();//FilelockerConnection.Instance.FILE_SECTION_KVP_LIST[indexPath.Section].Value[indexPath.Row];
				//cell = new UserSearchTableCell(rowUser);
				return cell;
			} 
			
			public override void RowSelected (UITableView tableView, MonoTouch.Foundation.NSIndexPath indexPath)
			{
//				FLFile rowFile = FilelockerConnection.Instance.FILE_SECTION_KVP_LIST[indexPath.Section].Value[indexPath.Row];
//				FileInfoView fivc = new FileInfoView(rowFile);
//				controller.NavigationController.PushViewController(fivc, true);
			}
			
			public override void CommitEditingStyle(UITableView tableView, UITableViewCellEditingStyle editingStyle, NSIndexPath indexPath)
			{
				if (editingStyle == UITableViewCellEditingStyle.Delete)
				{
					
				}
			}
		}
		
//		public partial class UserSearchTableCell : UITableViewCell
//		{
//			public UserSearchTableCell (User sourceUser) : base(UITableViewCellStyle.Subtitle, "UserSearchTableCel")
//			{
//				this.TextLabel.Text = sourceUser.userDisplayName;
//				this.DetailTextLabel.Text = sourceUser.userId;
//				this.ImageView.Image = UIImage.FromFile("Images/111-user.png");
//			}
//		}
		#endregion
	}
}

