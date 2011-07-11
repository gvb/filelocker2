using System;
using MonoTouch.UIKit;
using System.Collections.Generic;
using MonoTouch.Foundation;
using System.Threading;
using System.Drawing;
namespace Filelocker
{
	public partial class SettingsViewController : UIViewController
	{	
		List<KeyValuePair<string, string>> servers;
		UIPickerView uipv;
		UIAlertView _alert;
		UIActivityIndicatorView _ai;
		public SettingsViewController (IntPtr handle) : base(handle)
		{
			Initialize ();
		}

		[Export("initWithCoder:")]
		public SettingsViewController (NSCoder coder) : base(coder)
		{
			Initialize ();
		}

		public SettingsViewController () : base("SettingsViewController", null)
		{
			Initialize ();
		}

		void Initialize ()
		{
		}
		
		public override void ViewDidLoad() 
		{
			base.ViewDidLoad();
			servers = new List<KeyValuePair<string, string>>();
			tblLogin.Source = new LoginTableSource();
			btnVerify.TouchUpInside += delegate {
				string password = ((LoginTableSource)tblLogin.Source).PasswordEntry.Text;
				string username = ((LoginTableSource)tblLogin.Source).UsernameEntry.Text;
				string server = ((LoginTableSource)tblLogin.Source).ServerEntry.Text;
				lblStatus.TextAlignment = UITextAlignment.Center;
				try{
					string cliKey = FilelockerConnection.Instance.registerWithServer(server, username, password);
					NSUserDefaults.StandardUserDefaults.SetString(server, "server");
					NSUserDefaults.StandardUserDefaults.SetString(username, "username");
					NSUserDefaults.StandardUserDefaults.SetString(cliKey, "clikey");
					lblStatus.TextColor = UIColor.White;
					lblStatus.Text = "Connected! Client Registered.";
					this.TabBarController.SelectedIndex = 0;
				}
				catch (FilelockerException fe)
				{
					lblStatus.TextColor = UIColor.Red;
					lblStatus.Text = fe.Message;
				}
			};
			btnRefresh.TouchUpInside += delegate {
				var thread = new Thread(UpdateServers as ThreadStart);
				btnRefresh.SetTitle("Updating Servers...", UIControlState.Normal);
				UIActivityIndicatorView iv = new UIActivityIndicatorView(new RectangleF(0,0,40,40));
				iv.ActivityIndicatorViewStyle = UIActivityIndicatorViewStyle.Gray;
				thread.Start();
			};
			
			UITextField serverEntry = ((LoginTableSource)tblLogin.Source).ServerEntry;
			UIView keyboardView = serverEntry.InputView;

			//Build picker view
			ServerPickerDataModel spm = new ServerPickerDataModel(serverEntry, servers);
			uipv = new UIPickerView(new RectangleF(0,0,320,216));
			uipv.Model = spm;
			UIView pickerView = new UIView(uipv.Bounds);
			pickerView.AddSubview(uipv);
			//Picker built
			
			//Close Buttons
			UIBarButtonItem closeButton1 = new UIBarButtonItem();
			closeButton1.Title = "Close";
			closeButton1.Width = 160;
			closeButton1.Clicked += delegate {
				serverEntry.ResignFirstResponder();
			};
			UIBarButtonItem closeButton2 = new UIBarButtonItem();
			closeButton2.Title = "Close";
			closeButton2.Width = 160;
			closeButton2.Clicked += delegate {
				serverEntry.ResignFirstResponder();
			};
			//Build picker accessory toolbar
			UIBarButtonItem[] paBarButtonItems = new UIBarButtonItem[2];
			UIToolbar paBar = new UIToolbar(new RectangleF(0, 0, 320, 30));
			UIBarButtonItem keyboardButton = new UIBarButtonItem();
			keyboardButton.Title = "Specify Server";
			keyboardButton.Width = 160;
			paBarButtonItems[0] = keyboardButton;
			paBarButtonItems[1] = closeButton1;
			paBar.SetItems(paBarButtonItems, true);
			
			
			//Build Keyboard accessory toolbar
			UIBarButtonItem[] kaBarButtonItems = new UIBarButtonItem[2];
			UIToolbar kaBar = new UIToolbar(new RectangleF(0, 0, 320, 30));
			UIBarButtonItem pickerButton = new UIBarButtonItem();
			pickerButton.Title = "Known Servers";
			pickerButton.Width = 160;
			kaBarButtonItems[0] = pickerButton;
			kaBarButtonItems[1] = closeButton2;
			kaBar.SetItems(kaBarButtonItems, true);
			//Set up delegates
			pickerButton.Clicked += delegate {
				serverEntry.InputView = pickerView;
				serverEntry.InputAccessoryView = paBar;
				serverEntry.ResignFirstResponder();
				serverEntry.BecomeFirstResponder();
				};
			keyboardButton.Clicked += delegate {
				serverEntry.InputView = keyboardView;
				serverEntry.InputAccessoryView = kaBar;
				serverEntry.ResignFirstResponder();
				serverEntry.BecomeFirstResponder();
			};
			//Start with picker view
			serverEntry.InputView = pickerView;
			serverEntry.InputAccessoryView = paBar;
			
		}
		[Export("UpdateServers")]
		void UpdateServers()
		{
			using(var pool = new NSAutoreleasePool())
			{
				try
				{
					FilelockerConnection.Instance.updateKnownServers();
					HideAlert();

				}
				catch (FilelockerException fle)
				{
					Console.WriteLine("Problem updating servers: {0}", fle.Message);
					HideAlert();
				}
			}
		}
		public void ShowAlert(string message)
		{
			_alert = new UIAlertView(message, String.Empty, null, "OK", null);
	        _ai = new UIActivityIndicatorView();
	        _ai.Frame = new System.Drawing.RectangleF(125,50,40,40);
	        _ai.ActivityIndicatorViewStyle = UIActivityIndicatorViewStyle.WhiteLarge;
	        _alert.AddSubview(_ai);
	        _ai.StartAnimating();
	        _alert.Show();
		}
		public void HideAlert()
		{
			InvokeOnMainThread(delegate {
				servers = FilelockerConnection.Instance.readServersFile();
				ServerPickerDataModel spm = new ServerPickerDataModel(((LoginTableSource)tblLogin.Source).ServerEntry, servers);
				uipv.Model = spm;
				_alert.DismissWithClickedButtonIndex(0, true);
				});
		}
		public override void ViewWillAppear (bool animated)
		{
			base.ViewWillAppear (animated);
		}
		public override void ViewDidAppear (bool animated)
		{
			base.ViewDidAppear (animated);
			try
			{
				
				var documents = Environment.GetFolderPath(Environment.SpecialFolder.Personal);
				if (!System.IO.File.Exists(System.IO.Path.Combine(documents, "known_servers.xml")))
				{
					var thread = new Thread(UpdateServers as ThreadStart);
					ShowAlert("Getting Servers List");
					thread.Start();
				}
			}
			catch (FilelockerException fle)
			{
				Console.WriteLine("Unable to get the most recent list of servers: {0}", fle.Message);
			}
		}		
	}
}

