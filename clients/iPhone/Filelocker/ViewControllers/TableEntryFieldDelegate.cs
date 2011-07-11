using System;
using MonoTouch.UIKit;	
namespace Filelocker
{
	public class TableEntryFieldDelegate : UITextFieldDelegate
	{
		public TableEntryFieldDelegate ()
		{
		}
		
		public override bool ShouldReturn (UITextField textField)
		{
			textField.ResignFirstResponder();
			return true;
		}
	}
}

