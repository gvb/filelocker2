using System;
using System.IO;
using MonoTouch.Foundation;
namespace Filelocker
{
	public class ApplicationState
	{
		public static string FILES_PATH = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Personal), "files");
		public static string SERVERS_FILE = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Personal), "known_servers.xml");
		public static string FILES_CACHE = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Personal), "files.xml");
		public static string MESSAGES_CACHE = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Personal), "messages.xml");
		public static string SERVER = NSUserDefaults.StandardUserDefaults.StringForKey("server");
		public static string CLIKEY = NSUserDefaults.StandardUserDefaults.StringForKey("clikey");
		public static string USERID = NSUserDefaults.StandardUserDefaults.StringForKey("username");
		
		public ApplicationState ()
		{
		}
	}
}

