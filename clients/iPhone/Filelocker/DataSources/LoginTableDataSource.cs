using System;
using System.Drawing;
using MonoTouch.UIKit;
using MonoTouch.Foundation;
namespace Filelocker
{
	public class LoginTableSource : UITableViewSource
	{	
		public UITextField UsernameEntry { get; private set; }
		public UITextField PasswordEntry { get; private set; }
		public UITextField ServerEntry { get; private set; }
		
		public LoginTableSource () : base ()
		{
			BuildEntryFields();
		}
		public override string TitleForHeader (UITableView tableView, int section)
		{
			string sectionTitle = "";
		 	if (section == 0)
			{
				sectionTitle = "Login Information";
			}
			else if (section == 1)
			{
				sectionTitle = "Server URL";
			}
			else
			{
				sectionTitle = "Unknown";
			}
			return sectionTitle;
		}
		public override void RowSelected(UITableView tableView, NSIndexPath indexPath) 
		{
			tableView.DeselectRow (indexPath, false);
		}
		
		public override int NumberOfSections(UITableView tableview) 
		{
			return 2;
		}
		
		public override int RowsInSection (UITableView tableview, int section) 
		{
			int rows = 0;
			switch (section)
			{
				case 0:
					rows = 2;
					break;
				case 1:
					rows = 1;
					break;
			}
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
			switch (indexPath.Section)
			{
				case 0:
					switch (indexPath.Row)
					{
						case 0:
							cell.TextLabel.Text = "Username";
							cell.AccessoryView = UsernameEntry;
							break;
						case 1:
							cell.TextLabel.Text = "Password";
							cell.AccessoryView = PasswordEntry;
							break;
					}
					break;
				case 1:
					cell.TextLabel.Text = "URL";
					cell.AccessoryView = ServerEntry;
					break;
			}
			return cell;
		}
		
		private void BuildEntryFields()
		{
			TableEntryFieldDelegate entryDelegate = new TableEntryFieldDelegate();
			UsernameEntry = new UITextField (new RectangleF (0, 0, 190f, 30f)) {
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
			
			PasswordEntry = new UITextField(new RectangleF (0, 0, 190f, 30f)) {
						Text = "",
						Delegate = entryDelegate,
						VerticalAlignment = UIControlContentVerticalAlignment.Center,
						SecureTextEntry = true,
						AutocapitalizationType = UITextAutocapitalizationType.None,
						AutocorrectionType = UITextAutocorrectionType.No,
						ClearButtonMode = UITextFieldViewMode.WhileEditing,
						ReturnKeyType = UIReturnKeyType.Next,
						KeyboardType = UIKeyboardType.Default
					};
			string defaultServer = NSUserDefaults.StandardUserDefaults.StringForKey("server");
			
			ServerEntry = new UITextField(new RectangleF (0, 0, 190f, 30f)) {
						Text = !string.IsNullOrEmpty(defaultServer) ? defaultServer : "https://",
						Delegate = entryDelegate,
						VerticalAlignment = UIControlContentVerticalAlignment.Center,
						AutocapitalizationType = UITextAutocapitalizationType.None,
						AutocorrectionType = UITextAutocorrectionType.No,
						ClearButtonMode = UITextFieldViewMode.WhileEditing,
						ReturnKeyType = UIReturnKeyType.Done,
						KeyboardType = UIKeyboardType.Url
					};
			
			//PasswordEntry.EditingDidEnd += delegate { Password = PasswordEntry.Text; };
		}			
	}
}

