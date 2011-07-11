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
		// This method is invoked when the application has loaded its UI and its ready to run
		public override bool FinishedLaunching (UIApplication app, NSDictionary options)
		{
			if (!Directory.Exists(ApplicationState.FILES_PATH))
				Directory.CreateDirectory(ApplicationState.FILES_PATH);
			
			window.AddSubview(tabBarController.View);
			if (string.IsNullOrEmpty(ApplicationState.USERID) || string.IsNullOrEmpty(ApplicationState.CLIKEY) || string.IsNullOrEmpty(ApplicationState.SERVER))
			{
				tabBarController.SelectedIndex = 2;
				Console.WriteLine("Need to register");
			}
			else
			{
				try
				{
					if (!Login()) //Calling the Login function actually logs 
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
			
			return true;
		}
		
		public bool Login()
		{
			FilelockerConnection.Instance.login(ApplicationState.SERVER, ApplicationState.USERID, ApplicationState.CLIKEY);
			return FilelockerConnection.Instance.CONNECTED;
		}
		
		public void alert(string title, string message)
		{
			using(var alert = new UIAlertView(title, message, null, "OK", null))
			{
			    alert.Show();  
			}
		}
		
		public string GetFilePathByFileId(string fileId)
		{
			string filesPath = ApplicationState.FILES_PATH;
			string strFilePath = "";
			foreach (string filePath in System.IO.Directory.GetFiles(filesPath).ToList())
			{
				string fileName = System.IO.Path.GetFileName(filePath);
				try
				{
					string fileExtension = System.IO.Path.GetExtension(fileName);
					string foundFileId = fileName.Replace(fileExtension, "");
					if (foundFileId == fileId)
					{
						strFilePath = filePath;
						break;
					}
				}
				catch (Exception e)
				{
					Console.WriteLine("Filename {0} failed to remove extension: {1}", fileName, e.Message);
				}
			}
			return strFilePath;
		}

		
		// This method is required in iPhoneOS 3.0
		public override void OnActivated (UIApplication application)
		{
		}
	}
}