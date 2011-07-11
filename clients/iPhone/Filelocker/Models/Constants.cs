using System;
using System.Collections.Generic;
namespace Filelocker
{
	public class Constants
	{
		public static Dictionary<string, string> FILE_ICONS_BY_EXTENSION = new Dictionary<string, string>()
		{
			{"log", "Images/application_xp_terminal.png"},
			{"txt", "Images/page_white_text.png"},
			{"pdf", "Images/page_white_acrobat.png"},
			{"default", "Images/page_green.png"}
		};
		public static Dictionary<string, string> MESSAGE_ICONS = new Dictionary<string, string>()
		{
			{"read", "Images/email_open.png"},
			{"new", "Images/email.png"},
			{"sent", "Images/email_go.png"},
			{"default", "Images/email.png"}
		};
		//TODO: Make an enum of the tab indices
		public Constants ()
		{
		}
	}
}

