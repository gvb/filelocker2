using System;
using MonoTouch.UIKit;
using System.Collections.Generic;
namespace Filelocker
{
	public class FLMessage
	{
		public string messageId {get; set;}
		public string messageSubject {get; set;}
		public string messageBody {get; set;}
		public string messageOwnerId {get; set;}
		public string messageRecipients {get; set;}
		public DateTime messageCreateDatetime {get; set;}
    	public DateTime messageExpirationDatetime {get; set;}
		public DateTime messageViewedDatetime {get; set;}

		public FLMessage ()
		{
		}
	}
}

