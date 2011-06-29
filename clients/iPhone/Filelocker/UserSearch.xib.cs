
using System;
using System.Collections.Generic;
using System.Linq;
using System.Drawing;
using MonoTouch.Foundation;
using MonoTouch.UIKit;

namespace Filelocker
{
	public partial class UserSearch : UIViewController
	{
		#region Constructors

		// The IntPtr and initWithCoder constructors are required for items that need 
		// to be able to be created from a xib rather than from managed code

		public UserSearch (IntPtr handle) : base(handle)
		{
			Initialize ();
		}

		[Export("initWithCoder:")]
		public UserSearch (NSCoder coder) : base(coder)
		{
			Initialize ();
		}

		public UserSearch () : base("UserSearch", null)
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
		#endregion
		
	}
}