using System;
using System.Collections.Generic;
using System.Threading;
using System.Linq;
using System.IO;
using System.Drawing;
using MonoTouch.Foundation;
using MonoTouch.UIKit;

namespace Filelocker
{
	public delegate void CancelEventHandler(object sender, EventArgs e);
	public class Application
	{
		static void Main (string[] args)
		{
			UIApplication.Main (args);
		}		
	}

	// The name AppDelegate is referenced in the MainWindow.xib file.
	public partial class AppDelegate : UIApplicationDelegate
	{
		UITabBarController primaryViewController;
		UIAlertView loadingView;
		// This method is invoked when the application has loaded its UI and its ready to run
		public override bool FinishedLaunching (UIApplication app, NSDictionary options)
		{
			string server = NSUserDefaults.StandardUserDefaults.StringForKey("server");
			string cliKey = NSUserDefaults.StandardUserDefaults.StringForKey("clikey");
			string username = NSUserDefaults.StandardUserDefaults.StringForKey("username");
			window.AddSubview(tabBarController.View);
			if (string.IsNullOrEmpty(server) || string.IsNullOrEmpty(username) || string.IsNullOrEmpty(cliKey))
			{
				tabBarController.SelectedIndex = 2;
				Console.WriteLine("Need to register");
			}
			else
			{
				try
				{
					if (!login())
					{
						alert("Unable to Log In", "Your crendentials are no longer valid and you may need to re-register with the server");
						tabBarController.SelectedIndex = 2;
					}
				}
				catch (FilelockerException fe)
				{
					using(var alert = new UIAlertView("Login Failure", fe.Message, null, "OK", null))
					{
						alert.Show();
					}
				}
			}
			window.MakeKeyAndVisible ();
			//var thread = new Thread(StartDownload as ThreadStart);
			//thread.Start();
			
			return true;
		}
		
		public bool login()
		{
			string server = NSUserDefaults.StandardUserDefaults.StringForKey("server");
			string cliKey = NSUserDefaults.StandardUserDefaults.StringForKey("clikey");
			string username = NSUserDefaults.StandardUserDefaults.StringForKey("username");
			FilelockerConnection.Instance.login(server, username.Trim(), cliKey.Trim());
			return FilelockerConnection.Instance.connected;
		}
		
		public void alert(string title, string message)
		{
			using(var alert = new UIAlertView(title, message, null, "OK", null))
			{
			    alert.Show();  
			}
		}
		
		public void startLoading(string title, string message)
		{
			InvokeOnMainThread( delegate {
				loadingView = new UIAlertView(title, message, null, null, null);
				loadingView.Show();
				UIActivityIndicatorView indicator = new UIActivityIndicatorView(UIActivityIndicatorViewStyle.WhiteLarge);
				indicator.Center = new System.Drawing.PointF(loadingView.Bounds.Size.Width/2, loadingView.Bounds.Size.Height-50);
				indicator.StartAnimating();
				loadingView.AddSubview(indicator);	
			});
			
		}
		
		public void stopLoading()
		{
			InvokeOnMainThread(delegate {
				loadingView.DismissWithClickedButtonIndex(0, true);
			});
		}

		
		// This method is required in iPhoneOS 3.0
		public override void OnActivated (UIApplication application)
		{
		}
	}
}