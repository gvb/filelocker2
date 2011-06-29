
using System;
using System.Collections.Generic;
using System.Linq;
using MonoTouch.Foundation;
using MonoTouch.UIKit;

namespace Filelocker
{
	public partial class Register : UIViewController
	{
		#region Constructors

		// The IntPtr and initWithCoder constructors are required for items that need 
		// to be able to be created from a xib rather than from managed code

		public Register (IntPtr handle) : base(handle)
		{
			Initialize ();
		}

		[Export("initWithCoder:")]
		public Register (NSCoder coder) : base(coder)
		{
			Initialize ();
		}

		public Register () : base("Register", null)
		{
			Initialize ();
		}

		void Initialize ()
		{
		}
		
		public override void ViewDidLoad() 
		{
			base.ViewDidLoad();
			PopulateSettings();
			txtCLIKey.UserInteractionEnabled = false;
			txtServer.ShouldReturn = DoReturn;
			txtPassword.ShouldReturn = DoReturn;
			txtUsername.ShouldReturn = DoReturn;

			btnSaveSettings.TouchUpInside += BtnSaveSettingsTouchUpInside;
		}
		/// <summary>
		/// Populates our page from settings
		/// </summary>
		protected void PopulateSettings()
		{
			Console.WriteLine("Populating settings");
			this.txtServer.Text = NSUserDefaults.StandardUserDefaults.StringForKey("server");
			this.txtCLIKey.Text = NSUserDefaults.StandardUserDefaults.StringForKey("clikey");
			this.txtUsername.Text = NSUserDefaults.StandardUserDefaults.StringForKey("username");
		}
		
		protected void BtnSaveSettingsTouchUpInside (object sender, EventArgs e)
		{
			string username = txtUsername.Text;
			string cliKey = txtCLIKey.Text;
			string password = txtPassword.Text;
			string server = txtServer.Text;
			NSUserDefaults.StandardUserDefaults.SetString(string.IsNullOrEmpty(this.txtServer.Text) ? "" : this.txtServer.Text, "server");
			try
			{
				string registrationKey = FilelockerConnection.Instance.registerWithServer(server.Trim(), username.Trim(), password.Trim());
				txtCLIKey.Text = registrationKey;
				NSUserDefaults.StandardUserDefaults.SetString(string.IsNullOrEmpty(this.txtUsername.Text) ? "" : this.txtUsername.Text, "username");
				NSUserDefaults.StandardUserDefaults.SetString(string.IsNullOrEmpty(this.txtCLIKey.Text) ? "" : this.txtCLIKey.Text, "clikey");
				FilelockerConnection.Instance.login(server, username.Trim(), cliKey.Trim());
				if (FilelockerConnection.Instance.connected)
				{
					this.TabBarController.SelectedIndex = 0;
				}
			}
			catch (FilelockerException fe)
			{
				using(var alert = new UIAlertView("Registration Failed",fe.Message,null, "Ok"))
				{
				    alert.Show();  
				}
			}
			
		}
		private bool DoReturn(UITextField tf)
		{
			tf.ResignFirstResponder ();
			return true;
		}
		#endregion
	}
}

