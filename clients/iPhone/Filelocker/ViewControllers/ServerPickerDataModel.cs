using System;
using System.Collections.Generic;
using System.Drawing;
using MonoTouch.Foundation;
using MonoTouch.UIKit;
namespace Filelocker
{
	public class ServerPickerDataModel : UIPickerViewModel
	{	
		UITextField serverField;
		List<KeyValuePair<string, string>> Servers_Name_URL_List;
		public ServerPickerDataModel(UITextField tf, List<KeyValuePair<string, string>> snul)
		{
			serverField = tf;
			Servers_Name_URL_List = snul;
			
		}
		
		public override int GetComponentCount(UIPickerView uipv)
		{
			return(1);	
		}
		
		public override int GetRowsInComponent( UIPickerView uipv, int comp)
		{	
			//each component has its own count.	
			Console.WriteLine("Got the rows");
			int rows = Servers_Name_URL_List.Count;
			return(rows);
		}
		
		public override string GetTitle(UIPickerView uipv, int row, int comp)
		{
			//each component would get its own title.
			string output = Servers_Name_URL_List[row].Key;
			return(output);
		}
		
		public override void Selected(UIPickerView uipv, int row, int comp)
		{
			string pickerValue = Servers_Name_URL_List[row].Value;
			serverField.Text = pickerValue;			
		}
		
		public override float GetComponentWidth(UIPickerView uipv, int comp)
		{
			return(300f);
		}
		
		public override float GetRowHeight(UIPickerView uipv, int comp)
		{
			return(40f); 
		}
	}
}